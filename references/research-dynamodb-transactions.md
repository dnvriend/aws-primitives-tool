# DynamoDB TransactWriteItems and TransactGetItems API Research

## Executive Summary

### Topic Overview
This research covers DynamoDB's atomic transaction APIs - TransactWriteItems and TransactGetItems - which enable ACID-compliant operations across multiple items and tables within a single AWS Region. These APIs are critical for implementing robust key-value store primitives that require atomic multi-item operations.

### Key Findings
- **Transaction Scope**: Up to 100 distinct items per transaction, maximum 4 MB aggregate size
- **Operations Supported**: Put, Update, Delete, and ConditionCheck for writes; Get for reads
- **Atomicity**: All-or-nothing execution with serializable isolation guarantees
- **Cost Model**: Transactions consume 2x capacity units compared to individual operations
- **Regional Constraint**: Transactions operate within a single AWS account and Region only
- **Idempotency**: Built-in support via ClientRequestToken (10-minute validity window)

### Relevance
For the kvstore project, these transaction APIs enable:
- Atomic multi-key operations (batch puts, conditional updates across items)
- Mixing different primitive types (kv, counter, lock) in single transactions
- Optimistic locking with version checking via ConditionCheck
- Safe concurrent operations with conflict detection

## Technical Analysis

### Service Architecture

#### TransactWriteItems API

**Purpose**: Synchronous, idempotent write operation grouping up to 100 actions atomically.

**Supported Actions**:
1. **Put** - Create new item or replace existing (conditional or unconditional)
2. **Update** - Modify existing item attributes or create if not exists
3. **Delete** - Remove item by primary key
4. **ConditionCheck** - Verify item existence or attribute conditions without modification

**Key Characteristics**:
- Synchronous operation (blocks until complete or fails)
- Idempotent with ClientRequestToken (prevents duplicate execution)
- Cannot target same item multiple times in one transaction
- Cannot use indexes (must operate on base tables only)
- Changes propagate gradually to GSIs, streams, and backups (not atomic)

#### TransactGetItems API

**Purpose**: Synchronous read operation atomically retrieving up to 100 items.

**Supported Actions**:
1. **Get** - Retrieve item by primary key with optional projection

**Key Characteristics**:
- All reads succeed or all fail (atomic snapshot)
- Cannot use indexes (must operate on base tables only)
- Provides consistent view across multiple items
- No condition expressions supported (read-only)

### Regional Availability

**Scope**: Transactions are available in all AWS Regions where DynamoDB is offered.

**Constraints**:
- Transactions cannot span multiple AWS accounts
- Transactions cannot span multiple Regions
- Global tables: ACID guarantees only in source Region; replicated Regions may observe partial transactions during propagation
- For global tables, avoid using transactions across Regions

### Implementation Patterns

#### Pattern 1: Atomic Multi-Item Write with Conditions

```python
import boto3

dynamodb = boto3.client('dynamodb')

response = dynamodb.transact_write_items(
    TransactItems=[
        {
            'Put': {
                'TableName': 'kvstore',
                'Item': {
                    'pk': {'S': 'key1'},
                    'sk': {'S': 'kv#metadata'},
                    'value': {'S': 'value1'},
                    'version': {'N': '1'}
                },
                'ConditionExpression': 'attribute_not_exists(pk)'
            }
        },
        {
            'Update': {
                'TableName': 'kvstore',
                'Key': {
                    'pk': {'S': 'counter1'},
                    'sk': {'S': 'counter#metadata'}
                },
                'UpdateExpression': 'ADD #count :inc SET #version = #version + :inc',
                'ExpressionAttributeNames': {
                    '#count': 'count',
                    '#version': 'version'
                },
                'ExpressionAttributeValues': {
                    ':inc': {'N': '1'}
                },
                'ConditionExpression': 'attribute_exists(pk)'
            }
        },
        {
            'ConditionCheck': {
                'TableName': 'kvstore',
                'Key': {
                    'pk': {'S': 'lock1'},
                    'sk': {'S': 'lock#metadata'}
                },
                'ConditionExpression': 'attribute_not_exists(pk) OR #owner = :requester',
                'ExpressionAttributeNames': {
                    '#owner': 'owner'
                },
                'ExpressionAttributeValues': {
                    ':requester': {'S': 'client-123'}
                }
            }
        }
    ],
    ClientRequestToken='unique-idempotency-token-12345'
)
```

#### Pattern 2: Optimistic Locking with Version Check

```python
# Read current version
response = dynamodb.get_item(
    TableName='kvstore',
    Key={'pk': {'S': 'key1'}, 'sk': {'S': 'kv#metadata'}}
)
current_version = int(response['Item']['version']['N'])

# Update with version check
try:
    dynamodb.transact_write_items(
        TransactItems=[
            {
                'Update': {
                    'TableName': 'kvstore',
                    'Key': {
                        'pk': {'S': 'key1'},
                        'sk': {'S': 'kv#metadata'}
                    },
                    'UpdateExpression': 'SET #value = :new_value, #version = :new_version',
                    'ConditionExpression': '#version = :expected_version',
                    'ExpressionAttributeNames': {
                        '#value': 'value',
                        '#version': 'version'
                    },
                    'ExpressionAttributeValues': {
                        ':new_value': {'S': 'updated_value'},
                        ':new_version': {'N': str(current_version + 1)},
                        ':expected_version': {'N': str(current_version)}
                    }
                }
            }
        ]
    )
except dynamodb.exceptions.TransactionCanceledException as e:
    # Handle version conflict (optimistic lock failure)
    print(f"Transaction failed: {e.response['CancellationReasons']}")
```

#### Pattern 3: Atomic Batch Read with TransactGetItems

```python
response = dynamodb.transact_get_items(
    TransactItems=[
        {
            'Get': {
                'TableName': 'kvstore',
                'Key': {
                    'pk': {'S': 'key1'},
                    'sk': {'S': 'kv#metadata'}
                },
                'ProjectionExpression': '#pk, #value, #version',
                'ExpressionAttributeNames': {
                    '#pk': 'pk',
                    '#value': 'value',
                    '#version': 'version'
                }
            }
        },
        {
            'Get': {
                'TableName': 'kvstore',
                'Key': {
                    'pk': {'S': 'counter1'},
                    'sk': {'S': 'counter#metadata'}
                }
            }
        },
        {
            'Get': {
                'TableName': 'kvstore',
                'Key': {
                    'pk': {'S': 'lock1'},
                    'sk': {'S': 'lock#metadata'}
                }
            }
        }
    ],
    ReturnConsumedCapacity='TOTAL'
)

# All items retrieved atomically
items = [resp.get('Item') for resp in response['Responses']]
```

#### Pattern 4: Conditional Multi-Item Delete

```python
dynamodb.transact_write_items(
    TransactItems=[
        {
            'Delete': {
                'TableName': 'kvstore',
                'Key': {
                    'pk': {'S': 'key1'},
                    'sk': {'S': 'kv#metadata'}
                },
                'ConditionExpression': 'attribute_exists(pk) AND #version = :expected',
                'ExpressionAttributeNames': {
                    '#version': 'version'
                },
                'ExpressionAttributeValues': {
                    ':expected': {'N': '5'}
                }
            }
        },
        {
            'Delete': {
                'TableName': 'kvstore',
                'Key': {
                    'pk': {'S': 'key2'},
                    'sk': {'S': 'kv#metadata'}
                },
                'ConditionExpression': 'attribute_exists(pk)'
            }
        }
    ]
)
```

### Configuration Details

#### Request Parameters

**TransactWriteItems**:
- `TransactItems` (required): Array of 1-100 TransactWriteItem objects
- `ClientRequestToken` (optional): UUID for idempotency (10-minute validity)
- `ReturnConsumedCapacity`: NONE, TOTAL, or INDEXES
- `ReturnItemCollectionMetrics`: SIZE or NONE

**TransactGetItems**:
- `TransactItems` (required): Array of 1-100 TransactGetItem objects
- `ReturnConsumedCapacity`: NONE, TOTAL, or INDEXES

#### Condition Expressions

Transactions support full DynamoDB condition expression syntax:

**Comparison Operators**: `=`, `<>`, `<`, `<=`, `>`, `>=`

**Logical Operators**: `AND`, `OR`, `NOT`

**Functions**:
- `attribute_exists(path)` - Check if attribute exists
- `attribute_not_exists(path)` - Check if attribute does not exist
- `attribute_type(path, type)` - Check attribute type
- `begins_with(path, substr)` - String prefix match
- `contains(path, operand)` - String/set contains check
- `size(path)` - Get attribute size

**Example Conditions**:
```python
# Check item doesn't exist
'attribute_not_exists(pk)'

# Version check for optimistic locking
'#version = :expected_version'

# Multi-condition check
'attribute_exists(pk) AND #status = :active AND #count > :threshold'

# Check attribute type
'attribute_type(#data, :string_type)'

# String prefix match
'begins_with(#key, :prefix)'
```

### Performance Considerations

#### Capacity Consumption

**Write Transactions**:
- Standard writes: 2 WCUs per KB (double standard write cost)
- Transactional writes require 2 write operations per item:
  - 1 prepare phase
  - 1 commit phase

**Read Transactions**:
- Standard reads: 2 RCUs per 4 KB for strongly consistent (double standard read cost)
- Eventually consistent not supported in transactions
- All reads in transaction are strongly consistent

**Calculation Examples**:

```
Example 1: Transaction writing 3 items (1 KB each)
- Standard write cost: 3 items × 1 WCU = 3 WCUs
- Transaction write cost: 3 items × 2 WCUs = 6 WCUs

Example 2: Transaction reading 5 items (4 KB each)
- Standard strongly consistent read: 5 items × 1 RCU = 5 RCUs
- Transaction read cost: 5 items × 2 RCUs = 10 RCUs

Example 3: Mixed transaction (2 puts, 1 update, 1 delete, 1 condition check)
- Total items affected: 5
- Capacity cost: 5 items × 2 WCUs = 10 WCUs (assuming 1 KB items)
```

#### Throughput Considerations

- Transactions count against table and GSI provisioned capacity
- Enable auto-scaling for tables using transactions
- Monitor `TransactionConflict` CloudWatch metric
- Transactions may be throttled if insufficient capacity

#### Latency Characteristics

- Typical latency: 2-3x single-item operation latency
- Latency increases with number of items in transaction
- Cross-table transactions may have higher latency
- Network round-trip is synchronous (blocking)

### Security & Compliance

#### IAM Permissions Required

**Write Transactions**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:ConditionCheckItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:region:account:table/kvstore"
            ]
        }
    ]
}
```

**Read Transactions**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:region:account:table/kvstore"
            ]
        }
    ]
}
```

#### Encryption & Compliance

- Transactions respect table encryption settings (AWS owned, AWS managed, or customer managed KMS keys)
- Data in transit encrypted via TLS/HTTPS
- Transactions provide ACID guarantees within single Region
- CloudTrail logs transaction API calls
- VPC endpoints supported for private connectivity

## Practical Guidance

### Best Practices

1. **Enable Auto-Scaling**
   - Transactions consume 2x capacity units
   - Set up CloudWatch alarms for `ConsumedReadCapacityUnits` and `ConsumedWriteCapacityUnits`
   - Consider on-demand billing for unpredictable workloads

2. **Use ClientRequestToken for Idempotency**
   - Always include ClientRequestToken for write transactions
   - Generate unique UUIDs for each logical transaction
   - Token valid for 10 minutes
   - Prevents duplicate execution on retries

3. **Avoid Grouping Unnecessary Operations**
   - Only include operations that must be atomic
   - Smaller transactions have lower latency
   - Reduces likelihood of conflicts

4. **Group Frequently Updated Attributes Together**
   - Store related attributes in same item to minimize transaction scope
   - Use composite attributes when possible
   - Reduces cross-item transaction needs

5. **Design for Conflict Handling**
   - Implement exponential backoff for retries
   - Monitor `TransactionConflict` metric
   - Use optimistic locking patterns with version attributes

6. **Partition Key Design**
   - Ensure high cardinality to avoid hot partitions
   - Distribute transaction load across partitions
   - Avoid transactions targeting same partition repeatedly

7. **Don't Use Transactions for Bulk Operations**
   - For ingesting large datasets, use BatchWriteItem instead
   - Transactions have 100-item limit
   - Consider parallel batch operations for bulk loads

### Common Pitfalls

1. **Same Item Multiple Times**
   - ERROR: Cannot target same item with multiple operations in one transaction
   - Solution: Combine operations into single Update action

2. **Exceeding 4 MB Aggregate Size**
   - ERROR: Transaction rejected if total item size > 4 MB
   - Solution: Break into multiple transactions or reduce item sizes

3. **Operating on Indexes**
   - ERROR: Transactions cannot target GSI or LSI directly
   - Solution: Always operate on base table; index updates happen automatically

4. **Cross-Region Transactions**
   - ERROR: Transactions cannot span Regions
   - Solution: Use separate transactions per Region

5. **Forgetting Version Checks**
   - PROBLEM: Concurrent updates may overwrite without conflict detection
   - Solution: Always use version attribute with ConditionExpression

6. **Not Handling TransactionCanceledException**
   - PROBLEM: Unhandled exceptions cause operation failures
   - Solution: Implement proper exception handling with CancellationReasons inspection

7. **Mixing Different Table Classes**
   - PROBLEM: Global table transactions may show partial results in replicas
   - Solution: Use TransactGetItems to read atomic snapshot

### Code Examples

#### Complete Transaction Error Handling

```python
import boto3
import uuid
import time
from botocore.exceptions import ClientError

dynamodb = boto3.client('dynamodb')

def execute_transaction_with_retry(transact_items, max_retries=3):
    """
    Execute DynamoDB transaction with exponential backoff retry logic.
    """
    for attempt in range(max_retries):
        try:
            response = dynamodb.transact_write_items(
                TransactItems=transact_items,
                ClientRequestToken=str(uuid.uuid4()),
                ReturnConsumedCapacity='TOTAL'
            )

            # Log capacity consumption
            total_capacity = sum(
                cap['CapacityUnits']
                for cap in response.get('ConsumedCapacity', [])
            )
            print(f"Transaction succeeded. Consumed {total_capacity} WCUs")
            return response

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'TransactionCanceledException':
                # Inspect cancellation reasons
                reasons = e.response['Error'].get('CancellationReasons', [])
                for idx, reason in enumerate(reasons):
                    if reason.get('Code') == 'ConditionalCheckFailed':
                        print(f"Item {idx}: Condition check failed")
                        if 'Item' in reason:
                            print(f"  Current item: {reason['Item']}")
                    elif reason.get('Code') == 'ItemCollectionSizeLimitExceeded':
                        print(f"Item {idx}: Collection size limit exceeded")
                    elif reason.get('Code') == 'TransactionConflict':
                        print(f"Item {idx}: Concurrent modification conflict")

                # Retry on conflicts with backoff
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.1  # Exponential backoff
                    print(f"Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print("Max retries reached")
                    raise

            elif error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException']:
                # Retry on throttling
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.1
                    print(f"Throttled. Retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    raise

            elif error_code == 'ValidationException':
                # Don't retry validation errors
                print(f"Validation error: {e.response['Error']['Message']}")
                raise

            else:
                # Unexpected error
                print(f"Unexpected error: {error_code}")
                raise

# Usage example
transact_items = [
    {
        'Put': {
            'TableName': 'kvstore',
            'Item': {
                'pk': {'S': 'key1'},
                'sk': {'S': 'kv#metadata'},
                'value': {'S': 'value1'},
                'version': {'N': '1'},
                'created_at': {'N': str(int(time.time()))}
            },
            'ConditionExpression': 'attribute_not_exists(pk)'
        }
    }
]

execute_transaction_with_retry(transact_items)
```

#### Kvstore-Specific Transaction Patterns

```python
class KvStoreTransactions:
    """Transaction utilities for kvstore primitives."""

    def __init__(self, table_name: str):
        self.dynamodb = boto3.client('dynamodb')
        self.table_name = table_name

    def atomic_multi_put(self, items: dict[str, str]) -> bool:
        """
        Atomically put multiple key-value pairs.
        All items must not exist (prevent overwrites).
        """
        transact_items = []
        for key, value in items.items():
            transact_items.append({
                'Put': {
                    'TableName': self.table_name,
                    'Item': {
                        'pk': {'S': key},
                        'sk': {'S': 'kv#metadata'},
                        'value': {'S': value},
                        'version': {'N': '1'},
                        'created_at': {'N': str(int(time.time()))}
                    },
                    'ConditionExpression': 'attribute_not_exists(pk)'
                }
            })

        try:
            self.dynamodb.transact_write_items(
                TransactItems=transact_items,
                ClientRequestToken=str(uuid.uuid4())
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                print("One or more items already exist")
                return False
            raise

    def compare_and_swap(self, key: str, expected: str, new_value: str) -> bool:
        """
        Atomically update value only if current value matches expected.
        Classic CAS operation using transactions.
        """
        try:
            self.dynamodb.transact_write_items(
                TransactItems=[
                    {
                        'Update': {
                            'TableName': self.table_name,
                            'Key': {
                                'pk': {'S': key},
                                'sk': {'S': 'kv#metadata'}
                            },
                            'UpdateExpression': 'SET #value = :new_value, #version = #version + :inc',
                            'ConditionExpression': '#value = :expected',
                            'ExpressionAttributeNames': {
                                '#value': 'value',
                                '#version': 'version'
                            },
                            'ExpressionAttributeValues': {
                                ':expected': {'S': expected},
                                ':new_value': {'S': new_value},
                                ':inc': {'N': '1'}
                            }
                        }
                    }
                ],
                ClientRequestToken=str(uuid.uuid4())
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                return False  # Value didn't match expected
            raise

    def atomic_increment_with_lock_check(self, counter_key: str, lock_key: str, owner: str) -> dict:
        """
        Atomically increment counter only if lock is held by owner.
        Demonstrates mixing counter and lock primitives in one transaction.
        """
        try:
            response = self.dynamodb.transact_write_items(
                TransactItems=[
                    {
                        'Update': {
                            'TableName': self.table_name,
                            'Key': {
                                'pk': {'S': counter_key},
                                'sk': {'S': 'counter#metadata'}
                            },
                            'UpdateExpression': 'ADD #count :inc SET #version = #version + :inc',
                            'ExpressionAttributeNames': {
                                '#count': 'count',
                                '#version': 'version'
                            },
                            'ExpressionAttributeValues': {
                                ':inc': {'N': '1'}
                            },
                            'ReturnValuesOnConditionCheckFailure': 'ALL_OLD'
                        }
                    },
                    {
                        'ConditionCheck': {
                            'TableName': self.table_name,
                            'Key': {
                                'pk': {'S': lock_key},
                                'sk': {'S': 'lock#metadata'}
                            },
                            'ConditionExpression': '#owner = :expected_owner',
                            'ExpressionAttributeNames': {
                                '#owner': 'owner'
                            },
                            'ExpressionAttributeValues': {
                                ':expected_owner': {'S': owner}
                            },
                            'ReturnValuesOnConditionCheckFailure': 'ALL_OLD'
                        }
                    }
                ],
                ClientRequestToken=str(uuid.uuid4()),
                ReturnConsumedCapacity='TOTAL'
            )
            return {'success': True, 'response': response}
        except ClientError as e:
            if e.response['Error']['Code'] == 'TransactionCanceledException':
                reasons = e.response['Error'].get('CancellationReasons', [])
                return {'success': False, 'reasons': reasons}
            raise

    def atomic_read_snapshot(self, keys: list[str]) -> dict[str, dict]:
        """
        Read multiple items atomically (consistent snapshot).
        """
        transact_items = []
        for key in keys:
            transact_items.append({
                'Get': {
                    'TableName': self.table_name,
                    'Key': {
                        'pk': {'S': key},
                        'sk': {'S': 'kv#metadata'}
                    }
                }
            })

        response = self.dynamodb.transact_get_items(
            TransactItems=transact_items,
            ReturnConsumedCapacity='TOTAL'
        )

        result = {}
        for idx, item_response in enumerate(response['Responses']):
            if item_response.get('Item'):
                key = keys[idx]
                result[key] = item_response['Item']

        return result
```

### Monitoring & Operations

#### CloudWatch Metrics

Monitor these metrics for transaction health:

1. **TransactionConflict** - Number of rejected transactions due to conflicts
2. **ConsumedReadCapacityUnits** - Track read capacity for TransactGetItems
3. **ConsumedWriteCapacityUnits** - Track write capacity for TransactWriteItems
4. **UserErrors** - Validation errors (e.g., invalid format, same item twice)
5. **SystemErrors** - Service-side errors requiring investigation
6. **ThrottledRequests** - Requests rejected due to capacity limits

#### CloudWatch Alarms

```python
# Example: Create alarm for high transaction conflicts
import boto3

cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_alarm(
    AlarmName='kvstore-high-transaction-conflicts',
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=2,
    MetricName='TransactionConflict',
    Namespace='AWS/DynamoDB',
    Period=300,
    Statistic='Sum',
    Threshold=10.0,
    ActionsEnabled=True,
    AlarmDescription='Alert when transaction conflicts exceed threshold',
    Dimensions=[
        {
            'Name': 'TableName',
            'Value': 'kvstore'
        }
    ]
)
```

#### Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

def log_transaction_result(transaction_type: str, items_count: int, result: dict):
    """Log transaction execution details."""
    if result.get('success'):
        capacity = sum(
            cap['CapacityUnits']
            for cap in result.get('response', {}).get('ConsumedCapacity', [])
        )
        logger.info(
            f"Transaction succeeded",
            extra={
                'transaction_type': transaction_type,
                'items_count': items_count,
                'capacity_units': capacity,
                'status': 'success'
            }
        )
    else:
        reasons = result.get('reasons', [])
        logger.warning(
            f"Transaction cancelled",
            extra={
                'transaction_type': transaction_type,
                'items_count': items_count,
                'cancellation_reasons': reasons,
                'status': 'cancelled'
            }
        )
```

## Comparative Analysis

### When to Use Transactions vs Individual Operations

| Scenario | Use Transactions | Use Individual Operations |
|----------|------------------|---------------------------|
| Multi-item atomicity required | Yes | No |
| Single item update | No | Yes |
| Read consistency across items needed | Yes (TransactGetItems) | No (use BatchGetItem) |
| Bulk data loading (>100 items) | No | Yes (BatchWriteItem) |
| Cost-sensitive workload | Consider carefully | Yes |
| Conditional operations on multiple items | Yes | No |
| Hot partition writes | Avoid | Yes |

### TransactWriteItems vs BatchWriteItem

| Feature | TransactWriteItems | BatchWriteItem |
|---------|-------------------|----------------|
| Atomicity | All-or-nothing | Best-effort (partial success possible) |
| Max items | 100 | 25 |
| Conditions | Yes (per item) | No |
| Capacity cost | 2x standard | 1x standard |
| Idempotency | Built-in (ClientRequestToken) | Manual |
| Conflict detection | Yes | No |
| Use case | ACID requirements | Bulk operations, eventual consistency OK |

### TransactGetItems vs BatchGetItem

| Feature | TransactGetItems | BatchGetItem |
|---------|------------------|-------------|
| Atomicity | All reads at same point in time | No atomicity guarantee |
| Max items | 100 | 100 |
| Consistency | Strongly consistent only | Eventually or strongly consistent |
| Capacity cost | 2x standard | 1x standard |
| Snapshot isolation | Yes | No |
| Use case | Consistent multi-item reads | High-throughput batch reads |

## Resources & References

### AWS Documentation

1. **Primary Transaction APIs Documentation**
   - TransactWriteItems API: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html
   - TransactGetItems API: https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactGetItems.html
   - Transaction How It Works: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html

2. **DynamoDB Constraints & Limits**
   - Constraints Documentation: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html
   - Transaction-specific limits section

3. **Condition Expressions**
   - Using Expressions: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.html
   - Condition Expression Examples: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html
   - Conditional Operations Examples: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/example_dynamodb_Scenario_ConditionalOperations_section.html

4. **Error Handling**
   - Error Handling with DynamoDB: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Programming.Errors.html

5. **Pricing Information**
   - On-Demand Pricing: https://aws.amazon.com/dynamodb/pricing/on-demand/
   - Provisioned Capacity Pricing: https://aws.amazon.com/dynamodb/pricing/provisioned/

### Related Services

- **DynamoDB Accelerator (DAX)**: Transactions supported with same isolation levels
- **DynamoDB Streams**: Transaction changes propagate gradually (not atomic in streams)
- **AWS Step Functions**: Can orchestrate complex multi-table workflows
- **CloudWatch**: Monitor transaction metrics and set alarms

### Community Resources

- AWS Blog: "Managing Complex Workflows with DynamoDB Transactions"
- AWS re:Invent sessions on DynamoDB transactions
- AWS SDK Documentation (boto3, AWS SDK for JavaScript, Java SDK)

## AWS CLI Tool Examples

### TransactWriteItems

```bash
# Atomic multi-item write with conditions
aws dynamodb transact-write-items \
    --transact-items '[
        {
            "Put": {
                "TableName": "kvstore",
                "Item": {
                    "pk": {"S": "key1"},
                    "sk": {"S": "kv#metadata"},
                    "value": {"S": "value1"},
                    "version": {"N": "1"}
                },
                "ConditionExpression": "attribute_not_exists(pk)"
            }
        },
        {
            "Update": {
                "TableName": "kvstore",
                "Key": {
                    "pk": {"S": "counter1"},
                    "sk": {"S": "counter#metadata"}
                },
                "UpdateExpression": "ADD #count :inc",
                "ExpressionAttributeNames": {
                    "#count": "count"
                },
                "ExpressionAttributeValues": {
                    ":inc": {"N": "1"}
                }
            }
        }
    ]' \
    --client-request-token "$(uuidgen)" \
    --return-consumed-capacity TOTAL
```

### TransactGetItems

```bash
# Atomic multi-item read (consistent snapshot)
aws dynamodb transact-get-items \
    --transact-items '[
        {
            "Get": {
                "TableName": "kvstore",
                "Key": {
                    "pk": {"S": "key1"},
                    "sk": {"S": "kv#metadata"}
                }
            }
        },
        {
            "Get": {
                "TableName": "kvstore",
                "Key": {
                    "pk": {"S": "key2"},
                    "sk": {"S": "kv#metadata"}
                },
                "ProjectionExpression": "pk, #v, version",
                "ExpressionAttributeNames": {
                    "#v": "value"
                }
            }
        }
    ]' \
    --return-consumed-capacity TOTAL
```

### ConditionCheck in Transaction

```bash
# Update with lock ownership check
aws dynamodb transact-write-items \
    --transact-items '[
        {
            "ConditionCheck": {
                "TableName": "kvstore",
                "Key": {
                    "pk": {"S": "lock1"},
                    "sk": {"S": "lock#metadata"}
                },
                "ConditionExpression": "#owner = :requester",
                "ExpressionAttributeNames": {
                    "#owner": "owner"
                },
                "ExpressionAttributeValues": {
                    ":requester": {"S": "client-123"}
                },
                "ReturnValuesOnConditionCheckFailure": "ALL_OLD"
            }
        },
        {
            "Update": {
                "TableName": "kvstore",
                "Key": {
                    "pk": {"S": "key1"},
                    "sk": {"S": "kv#metadata"}
                },
                "UpdateExpression": "SET #value = :new_value",
                "ExpressionAttributeNames": {
                    "#value": "value"
                },
                "ExpressionAttributeValues": {
                    ":new_value": {"S": "updated_by_lock_owner"}
                }
            }
        }
    ]'
```

## Answers to Key Questions

### 1. What operations does TransactWriteItems support?

**Four operation types**:
- **Put**: Create new item or replace existing (with optional conditions)
- **Update**: Modify existing item attributes or create if doesn't exist
- **Delete**: Remove item by primary key
- **ConditionCheck**: Verify conditions without modifying item

All operations support full condition expressions for atomic conditional logic.

### 2. What are the limits?

**Transaction Limits**:
- Maximum 100 unique items per transaction
- Maximum 4 MB aggregate size across all items
- Cannot target same item multiple times in one transaction
- Must operate within single AWS account and Region
- Cannot operate on indexes (base tables only)
- ClientRequestToken valid for 10 minutes

**Item Limits**:
- Maximum item size: 400 KB (includes attribute names and values)
- Maximum expression string: 4 KB
- Maximum expression attribute name/value: 255 bytes

### 3. How do conditional expressions work in transactions?

**Condition Expression Mechanics**:
- Each operation (Put, Update, Delete, ConditionCheck) can have its own ConditionExpression
- Conditions evaluated during transaction prepare phase
- If ANY condition fails, entire transaction is cancelled (all-or-nothing)
- Supports full expression syntax: comparisons, logical operators, functions
- `ReturnValuesOnConditionCheckFailure` returns current item state on failure

**Common Patterns**:
- Optimistic locking: `#version = :expected_version`
- Prevent overwrites: `attribute_not_exists(pk)`
- Ownership checks: `#owner = :requester`
- Range checks: `#balance >= :amount`

### 4. What error handling is needed for transaction conflicts?

**Primary Error: TransactionCanceledException**

**Cancellation Reasons**:
- `ConditionalCheckFailed`: Condition expression not met
- `ItemCollectionSizeLimitExceeded`: LSI collection > 10 GB
- `TransactionConflict`: Concurrent modification on same item
- `ProvisionedThroughputExceeded`: Insufficient capacity
- `ValidationException`: Invalid request format

**Handling Strategy**:
1. Catch `TransactionCanceledException`
2. Inspect `CancellationReasons` array (one entry per transaction item)
3. Implement exponential backoff for `TransactionConflict`
4. Log failed conditions with current item state
5. Don't retry validation errors
6. Use idempotency token to prevent duplicate execution on retries

### 5. What's the pricing model for transactions vs individual operations?

**Capacity Consumption**:

**Provisioned Mode**:
- Standard write: 1 WCU per KB
- Transaction write: 2 WCUs per KB (2x cost)
- Standard strongly consistent read: 1 RCU per 4 KB
- Transaction read: 2 RCUs per 4 KB (2x cost)

**On-Demand Mode** (as of November 2024 pricing reductions):
- Standard write: 1 WRU per KB
- Transaction write: 2 WRUs per KB (2x cost)
- Standard strongly consistent read: 1 RRU per 4 KB
- Transaction read: 2 RRUs per 4 KB (2x cost)

**Cost Comparison Example** (provisioned mode, us-east-1):
```
Scenario: 1 million writes of 1 KB items per day

Standard writes:
- Capacity: 1M × 1 WCU = 1M WCUs
- Cost: ~$0.47/month (provisioned)

Transaction writes:
- Capacity: 1M × 2 WCUs = 2M WCUs
- Cost: ~$0.94/month (provisioned)

Cost increase: 2x for ACID guarantees
```

**When Transaction Cost is Justified**:
- Atomicity required for data integrity
- Preventing compensation logic for partial failures
- Reducing application complexity
- Avoiding manual conflict resolution

### 6. Can you mix different item types in one transaction?

**YES - Full flexibility**:

Transactions can mix:
- Different item types (kv, counter, lock, set)
- Different tables (within same account/Region)
- Different operation types (Put, Update, Delete, ConditionCheck)

**Example: Cross-Primitive Transaction**:
```python
# Atomically: create KV item, increment counter, verify lock ownership
dynamodb.transact_write_items(
    TransactItems=[
        {
            'Put': {  # Create KV item
                'TableName': 'kvstore',
                'Item': {
                    'pk': {'S': 'user:123:profile'},
                    'sk': {'S': 'kv#metadata'},
                    'value': {'S': '{"name": "Alice"}'},
                    'version': {'N': '1'}
                }
            }
        },
        {
            'Update': {  # Increment counter
                'TableName': 'kvstore',
                'Key': {
                    'pk': {'S': 'stats:user_count'},
                    'sk': {'S': 'counter#metadata'}
                },
                'UpdateExpression': 'ADD #count :inc',
                'ExpressionAttributeNames': {'#count': 'count'},
                'ExpressionAttributeValues': {':inc': {'N': '1'}}
            }
        },
        {
            'ConditionCheck': {  # Verify lock
                'TableName': 'kvstore',
                'Key': {
                    'pk': {'S': 'lock:user_creation'},
                    'sk': {'S': 'lock#metadata'}
                },
                'ConditionExpression': '#owner = :requester',
                'ExpressionAttributeNames': {'#owner': 'owner'},
                'ExpressionAttributeValues': {':requester': {'S': 'worker-1'}}
            }
        }
    ]
)
```

**Constraints**:
- All items must be in same AWS account and Region
- Cannot exceed 100 items total
- Cannot exceed 4 MB aggregate size
- Cannot target same item (pk + sk) multiple times

### 7. What are best practices for transaction design?

**Design Principles**:

1. **Minimize Transaction Scope**
   - Only include operations that MUST be atomic
   - Smaller transactions = lower latency, fewer conflicts
   - Split large workflows into independent transactions where possible

2. **Design Data Model for Transactions**
   - Colocate frequently transacted attributes in same item
   - Use composite attributes to reduce transaction size
   - Design partition keys to avoid hot partitions

3. **Implement Idempotency**
   - Always use ClientRequestToken for write transactions
   - Store transaction IDs for audit trails
   - Handle duplicate execution gracefully

4. **Versioning & Optimistic Locking**
   - Include version attribute in all mutable items
   - Use version checks in ConditionExpression
   - Increment version on every update

5. **Error Handling Strategy**
   - Implement exponential backoff for conflicts
   - Inspect CancellationReasons for debugging
   - Log failed conditions with context
   - Use ReturnValuesOnConditionCheckFailure for diagnostics

6. **Capacity Planning**
   - Remember 2x capacity cost for transactions
   - Enable auto-scaling or use on-demand mode
   - Monitor TransactionConflict metric
   - Set CloudWatch alarms for throttling

7. **Testing & Validation**
   - Test concurrent transaction scenarios
   - Verify rollback behavior
   - Test timeout and retry logic
   - Load test with realistic transaction patterns

8. **Avoid Anti-Patterns**
   - Don't use transactions for bulk data loading
   - Don't group unrelated operations
   - Don't retry non-retryable errors (ValidationException)
   - Don't assume transaction propagation is immediate to streams/GSIs

---

**Report Generated**: 2025-11-16
**Research Scope**: DynamoDB TransactWriteItems and TransactGetItems APIs
**Target Use Case**: kvstore project atomic transaction implementation
