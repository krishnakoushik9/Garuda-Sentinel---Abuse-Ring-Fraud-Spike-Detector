import 'dart:ui';
import 'package:flutter/material.dart';

enum RiskLevel { clean, suspicious, mule }

class Account {
  final String accountId;
  final String customerName;
  final String riskProfile;
  final Map<String, dynamic> raw;

  Account({
    required this.accountId,
    required this.customerName,
    required this.riskProfile,
    required this.raw,
  });

  factory Account.fromJson(Map<String, dynamic> json) {
    return Account(
      accountId: json['account_id']?.toString() ?? json['id']?.toString() ?? '',
      customerName: json['customer_name']?.toString() ??
          json['name']?.toString() ??
          'Unknown',
      riskProfile: json['risk_profile']?.toString() ?? '',
      raw: json,
    );
  }

  RiskLevel get riskLevel {
    final rp = riskProfile.toUpperCase();
    if (rp.contains('HIGH') || rp.contains('MULE')) return RiskLevel.mule;
    if (rp.contains('MEDIUM') || rp.contains('SUSPICIOUS')) {
      return RiskLevel.suspicious;
    }
    return RiskLevel.clean;
  }

  double get balance {
    final b = raw['balance'];
    if (b is num) return b.toDouble();
    return fakeBalance.toDouble();
  }

  // Deterministic fake balance using account_id hash
  int get fakeBalance {
    int hash = 0;
    for (final ch in accountId.codeUnits) {
      hash = (hash * 31 + ch) & 0x7FFFFFFF;
    }
    return (hash * 1337) % 500000 + 5000;
  }

  String get formattedBalance {
    final b = fakeBalance;
    final s = b.toString();
    if (s.length <= 3) return '₹$s';
    final last3 = s.substring(s.length - 3);
    var rest = s.substring(0, s.length - 3);
    final buf = StringBuffer();
    int count = 0;
    for (int i = rest.length - 1; i >= 0; i--) {
      if (count > 0 && count % 2 == 0) buf.write(',');
      buf.write(rest[i]);
      count++;
    }
    final reversed = buf.toString().split('').reversed.join();
    return '₹$reversed,$last3';
  }

  String get maskedAccountId {
    if (accountId.length <= 4) return accountId;
    return '****${accountId.substring(accountId.length - 4)}';
  }

  Color get cardGradientStart {
    switch (riskLevel) {
      case RiskLevel.mule:
        return const Color(0xFF2C0A0A);
      case RiskLevel.suspicious:
        return const Color(0xFF1F1500);
      case RiskLevel.clean:
        return const Color(0xFF0A1F0A);
    }
  }

  Color get cardGradientEnd {
    switch (riskLevel) {
      case RiskLevel.mule:
        return const Color(0xFF1A0505);
      case RiskLevel.suspicious:
        return const Color(0xFF120E00);
      case RiskLevel.clean:
        return const Color(0xFF051205);
    }
  }

  String get riskBadgeLabel {
    switch (riskLevel) {
      case RiskLevel.mule:
        return 'MULE 🔴';
      case RiskLevel.suspicious:
        return 'SUSPICIOUS';
      case RiskLevel.clean:
        return 'CLEAN';
    }
  }

  Color get riskBadgeColor {
    switch (riskLevel) {
      case RiskLevel.mule:
        return const Color(0xFFFF453A);
      case RiskLevel.suspicious:
        return const Color(0xFFFF9F0A);
      case RiskLevel.clean:
        return const Color(0xFF30D158);
    }
  }
}
