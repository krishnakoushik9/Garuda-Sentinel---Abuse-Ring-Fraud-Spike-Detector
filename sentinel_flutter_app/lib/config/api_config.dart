import 'package:shared_preferences/shared_preferences.dart';

class ApiConfig {
  static const String defaultHost = 'localhost:8000';
  static const int timeoutSeconds = 10;

  static Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    final host = prefs.getString('backend_ip') ?? defaultHost;
    return 'http://$host';
  }

  static Future<void> setHost(String host) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('backend_ip', host);
  }

  // Endpoints
  static String accounts(String base, {int limit = 50}) =>
      '$base/api/v1/accounts/?limit=$limit';
  static String transactions(String base, {int limit = 30}) =>
      '$base/api/v1/transactions/?limit=$limit';
  static String investigate(String base, String txnId, String accountId) =>
      '$base/api/v1/investigate/?txn_id=$txnId&account_id=$accountId';
  static String investigationStatus(String base, String investigationId) =>
      '$base/api/v1/investigate/$investigationId/';
  static String graphCommunity(String base, int communityId) =>
      '$base/api/v1/graph/community/$communityId/';
  static String fraudRings(String base) =>
      '$base/api/v1/graph/fraud-rings/';
  static String graphStats(String base) =>
      '$base/api/v1/graph/stats/';
}
