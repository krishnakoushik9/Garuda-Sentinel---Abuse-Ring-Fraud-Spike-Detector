import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:postgres/postgres.dart';
import '../models/account.dart';
import '../models/transaction.dart';
import '../models/investigation.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  Connection? _connection;

  Future<Connection> _getConnection() async {
    if (_connection != null) {
      return _connection!;
    }

    try {
      _connection = await Connection.open(
        Endpoint(
          host: 'db.fvfbtxsdmeddzmktbjru.supabase.co',
          database: 'postgres',
          username: 'postgres',
          password: 'krishna1156@db',
          port: 5432,
        ),
        settings: const ConnectionSettings(
          sslMode: SslMode.require,
          connectTimeout: Duration(seconds: 15),
          queryTimeout: Duration(seconds: 15),
        ),
      );

      // Ensure investigations table exists
      await _connection!.execute('''
        CREATE TABLE IF NOT EXISTS investigations (
            id TEXT PRIMARY KEY,
            account_id TEXT,
            status TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
      ''');

      return _connection!;
    } catch (e) {
      print("Error connecting to Supabase PG: \$e");
      rethrow;
    }
  }

  Future<void> close() async {
    if (_connection != null) {
      try {
        await _connection!.close();
      } catch (_) {}
      _connection = null;
    }
  }

  Future<Result> _execute(Object query, {Map<String, dynamic>? parameters}) async {
    try {
      final conn = await _getConnection();
      return await conn.execute(query, parameters: parameters);
    } catch (e) {
      print("Execute query failed, retrying after reconnect. Error: \$e");
      await close();
      final conn = await _getConnection();
      return await conn.execute(query, parameters: parameters);
    }
  }

  Future<T> _runTx<T>(Future<T> Function(dynamic s) fn) async {
    try {
      final conn = await _getConnection();
      return await conn.runTx(fn);
    } catch (e) {
      print("Transaction execution failed, retrying after reconnect. Error: \$e");
      await close();
      final conn = await _getConnection();
      return await conn.runTx(fn);
    }
  }

  Future<List<Account>> fetchAccounts({int limit = 50}) async {
    try {
      final result = await _execute(
        Sql.named('SELECT * FROM accounts LIMIT @limit'),
        parameters: {'limit': limit},
      );

      return result.map((row) {
        final map = row.toColumnMap();
        if (map.containsKey('name') && !map.containsKey('customer_name')) {
          map['customer_name'] = map['name'];
        }
        return Account.fromJson(map);
      }).toList();
    } catch (e) {
      print("fetchAccounts error: \$e");
      rethrow;
    }
  }

  Future<List<Transaction>> fetchTransactions({int limit = 30}) async {
    try {
      final result = await _execute(
        Sql.named('SELECT * FROM transactions ORDER BY timestamp DESC LIMIT @limit'),
        parameters: {'limit': limit},
      );

      return result.map((row) {
        final map = row.toColumnMap();
        return Transaction.fromJson(map);
      }).toList();
    } catch (e) {
      print("fetchTransactions error: \$e");
      rethrow;
    }
  }

  Future<String> startInvestigation(String txnId, String accountId) async {
    try {
      final invId = 'INV-${DateTime.now().millisecondsSinceEpoch.toString().substring(5)}'
          '${List.generate(3, (_) => Random().nextInt(10)).join()}';

      await _execute(
        Sql.named('INSERT INTO investigations (id, account_id, status, result) VALUES (@id, @accountId, \'processing\', @result)'),
        parameters: {
          'id': invId,
          'accountId': accountId,
          'result': json.encode({'txn_id': txnId}),
        },
      );

      // Async background update to completed after 2.5 seconds (preserves UX loading animation)
      Future.delayed(const Duration(milliseconds: 2500), () async {
        try {
          final txnRes = await _execute(
            Sql.named('SELECT risk_score FROM transactions WHERE transaction_id = @txnId'),
            parameters: {'txnId': txnId},
          );
          double riskScore = 0.45;
          if (txnRes.isNotEmpty) {
            riskScore = (txnRes.first.toColumnMap()['risk_score'] as num).toDouble();
          }

          String verdict = 'CLEAN';
          String narrative = 'Transaction analysis complete. Node relationships appear standard and risk score is within acceptable bounds.';
          if (riskScore > 0.7) {
            verdict = 'FRAUD';
            narrative = 'Suspicious velocity and recipient matching signature. The transaction exhibits behavioral features aligned with coordinated mule accounts.';
          } else if (riskScore > 0.4) {
            verdict = 'SUSPICIOUS';
            narrative = 'Elevated transaction amount. Recommended for manual verification.';
          }

          final resultJson = json.encode({
            'investigation_id': invId,
            'status': 'completed',
            'final_risk_score': riskScore,
            'final_verdict': verdict,
            'explanation_narrative': narrative,
            'txn_id': txnId,
          });

          await _execute(
            Sql.named('UPDATE investigations SET status = \'completed\', result = @result WHERE id = @id'),
            parameters: {
              'id': invId,
              'result': resultJson,
            },
          );
        } catch (e) {
          print("Background investigation update error: \$e");
        }
      });

      return invId;
    } catch (e) {
      print("startInvestigation error: \$e");
      rethrow;
    }
  }

  Future<Investigation> getInvestigation(String investigationId) async {
    try {
      final result = await _execute(
        Sql.named('SELECT id, account_id, status, result FROM investigations WHERE id = @id'),
        parameters: {'id': investigationId},
      );
      if (result.isEmpty) {
        throw HttpException('Investigation not found');
      }
      final row = result.first.toColumnMap();
      final resultStr = row['result'] as String?;
      Map<String, dynamic> resultDict = {};
      if (resultStr != null && resultStr.isNotEmpty) {
        resultDict = json.decode(resultStr) as Map<String, dynamic>;
      }
      return Investigation.fromJson({
        'investigation_id': row['id'],
        'account_id': row['account_id'],
        'status': row['status'],
        ...resultDict,
      });
    } catch (e) {
      print("getInvestigation error: \$e");
      rethrow;
    }
  }

  Future<Map<String, dynamic>> fetchGraphCommunity(int communityId) async {
    try {
      // Fetch nodes from graph_analytics joined with accounts
      final nodeRes = await _execute(
        'SELECT g.account_id, g.pagerank, g.degree_centrality, g.community_id, a.risk_profile, a.name '
        'FROM graph_analytics g '
        'JOIN accounts a ON g.account_id = a.account_id '
        'LIMIT 30'
      );

      final List<Map<String, dynamic>> nodes = [];
      final List<String> accountIds = [];
      if (nodeRes.isEmpty) {
        final accRes = await _execute('SELECT account_id, name, risk_profile, balance FROM accounts LIMIT 20');
        for (final row in accRes) {
          final m = row.toColumnMap();
          nodes.add({
            'id': m['account_id'],
            'label': m['name'],
            'pagerank': 0.15 + (Random().nextDouble() * 0.4),
            'risk_level': m['risk_profile'],
            'risk_profile': m['risk_profile'],
          });
          accountIds.add(m['account_id'] as String);
        }
      } else {
        for (final row in nodeRes) {
          final m = row.toColumnMap();
          nodes.add({
            'id': m['account_id'],
            'label': m['name'] ?? m['account_id'],
            'pagerank': (m['pagerank'] as num?)?.toDouble() ?? 0.3,
            'risk_level': m['risk_profile'] ?? 'LOW',
            'risk_profile': m['risk_profile'] ?? 'LOW',
          });
          accountIds.add(m['account_id'] as String);
        }
      }

      // Fetch edges from account_relationships or transactions
      final List<Map<String, dynamic>> edges = [];
      if (accountIds.isNotEmpty) {
        final edgeRes = await _execute(
          Sql.named('SELECT source_account, target_account, strength FROM account_relationships '
                    'WHERE source_account = ANY(@accounts) OR target_account = ANY(@accounts) '
                    'LIMIT 50'),
          parameters: {'accounts': accountIds},
        );

        if (edgeRes.isEmpty) {
          final txRes = await _execute(
            Sql.named('SELECT sender_account, receiver_account, amount FROM transactions '
                      'WHERE sender_account = ANY(@accounts) OR receiver_account = ANY(@accounts) '
                      'LIMIT 50'),
            parameters: {'accounts': accountIds},
          );
          for (final row in txRes) {
            final m = row.toColumnMap();
            edges.add({
              'source': m['sender_account'],
              'target': m['receiver_account'],
              'weight': 1.0,
            });
          }
        } else {
          for (final row in edgeRes) {
            final m = row.toColumnMap();
            edges.add({
              'source': m['source_account'],
              'target': m['target_account'],
              'weight': (m['strength'] as num?)?.toDouble() ?? 1.0,
            });
          }
        }
      }

      return {
        'nodes': nodes,
        'edges': edges,
      };
    } catch (e) {
      print("fetchGraphCommunity error: \$e");
      rethrow;
    }
  }

  Future<List<dynamic>> fetchFraudRings() async {
    try {
      final result = await _execute('SELECT DISTINCT chain_id FROM mule_accounts LIMIT 10');
      return result.map((row) => {'ring_id': row[0]?.toString() ?? '1'}).toList();
    } catch (e) {
      print("fetchFraudRings error: \$e");
      return [];
    }
  }

  Future<Map<String, dynamic>> fetchGraphStats() async {
    try {
      final accCountRes = await _execute('SELECT COUNT(*) FROM accounts');
      final txnCountRes = await _execute('SELECT COUNT(*) FROM transactions');
      final fraudCountRes = await _execute('SELECT COUNT(*) FROM fraud_events');
      final muleCountRes = await _execute('SELECT COUNT(*) FROM mule_accounts');

      final totalAccounts = accCountRes.first[0] as int;
      final totalTransactions = txnCountRes.first[0] as int;
      final highRiskCount = fraudCountRes.first[0] as int;
      final muleCount = muleCountRes.first[0] as int;

      return {
        'node_count': totalAccounts,
        'nodes': totalAccounts,
        'edges': totalTransactions,
        'total_nodes': totalAccounts,
        'total_edges': totalTransactions,
        'mule_nodes': muleCount,
        'fraud_events': highRiskCount,
        'is_offline': false,
      };
    } catch (e) {
      print("fetchGraphStats error: \$e");
      rethrow;
    }
  }

  Future<Map<String, dynamic>> sendTransaction({
    required String senderAccount,
    required String receiverAccount,
    required double amount,
    required String channel,
    String? description,
  }) async {
    try {
      final txnId = 'TXN_${DateTime.now().millisecondsSinceEpoch.toString().substring(5)}'
          '${List.generate(4, (_) => Random().nextInt(10)).join()}';
      final timestamp = DateTime.now().toUtc().toIso8601String();

      // 1. Fetch sender balance
      final senderRes = await _execute(
        Sql.named('SELECT balance FROM accounts WHERE account_id = @senderAccount'),
        parameters: {'senderAccount': senderAccount},
      );
      if (senderRes.isEmpty) {
        throw HttpException('Sender account not found');
      }
      final double senderBal = (senderRes.first.toColumnMap()['balance'] as num).toDouble();

      if (senderBal < amount) {
        throw HttpException('Insufficient Balance');
      }

      // 2. Fetch receiver
      final receiverRes = await _execute(
        Sql.named('SELECT balance FROM accounts WHERE account_id = @receiverAccount'),
        parameters: {'receiverAccount': receiverAccount},
      );
      if (receiverRes.isEmpty) {
        throw HttpException('Receiver account not found');
      }

      // Determine risk score
      double riskScore = 0.05;
      if (amount >= 100000) {
        riskScore = 0.85;
      } else if (amount >= 10000) {
        riskScore = 0.45;
      }

      // Check if receiver account is registered as mule
      final muleRes = await _execute(
        Sql.named('SELECT 1 FROM mule_accounts WHERE account_id = @receiverAccount LIMIT 1'),
        parameters: {'receiverAccount': receiverAccount},
      );
      if (muleRes.isNotEmpty || amount == 9900.0) {
        riskScore = 0.92;
      }

      // 3. Update balances and insert transaction in a transaction!
      await _runTx((tx) async {
        await tx.execute(
          Sql.named('UPDATE accounts SET balance = balance - @amount WHERE account_id = @senderAccount'),
          parameters: {'amount': amount, 'senderAccount': senderAccount},
        );
        await tx.execute(
          Sql.named('UPDATE accounts SET balance = balance + @amount WHERE account_id = @receiverAccount'),
          parameters: {'amount': amount, 'receiverAccount': receiverAccount},
        );
        await tx.execute(
          Sql.named('INSERT INTO transactions (transaction_id, timestamp, sender_account, receiver_account, amount, channel, status, description, risk_score) '
                    'VALUES (@txnId, @timestamp, @senderAccount, @receiverAccount, @amount, @channel, \'COMPLETED\', @description, @riskScore)'),
          parameters: {
            'txnId': txnId,
            'timestamp': timestamp,
            'senderAccount': senderAccount,
            'receiverAccount': receiverAccount,
            'amount': amount,
            'channel': channel,
            'description': description ?? '',
            'riskScore': riskScore,
          },
        );

        // If risk score is high, insert into fraud_events
        if (riskScore > 0.5) {
          final eventId = 'FE-IF-${DateTime.now().millisecondsSinceEpoch.toString().substring(8)}'
              '${List.generate(3, (_) => Random().nextInt(10)).join()}';
          final desc = riskScore > 0.9
              ? 'Mule account warning matched. Elevated danger risk flag.'
              : 'High value transaction transaction velocity check triggered.';

          await tx.execute(
            Sql.named('INSERT INTO fraud_events (event_id, transaction_id, account_id, fraud_type, description, severity, detected_at) '
                      'VALUES (@eventId, @txnId, @senderAccount, @fraudType, @description, @severity, @detectedAt)'),
            parameters: {
              'eventId': eventId,
              'txnId': txnId,
              'senderAccount': senderAccount,
              'fraudType': riskScore > 0.9 ? 'MULE_TRANSFER' : 'HIGH_VALUE_VELOCITY',
              'description': desc,
              'severity': riskScore > 0.9 ? 'HIGH' : 'MEDIUM',
              'detectedAt': timestamp,
            },
          );
        }
      });

      return {
        'transaction_id': txnId,
        'timestamp': timestamp,
        'sender_account': senderAccount,
        'receiver_account': receiverAccount,
        'amount': amount,
        'channel': channel,
        'status': 'COMPLETED',
        'description': description ?? '',
        'risk_score': riskScore,
      };
    } catch (e) {
      print("sendTransaction error: \$e");
      rethrow;
    }
  }
}
