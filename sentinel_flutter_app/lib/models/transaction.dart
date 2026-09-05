class Transaction {
  final String transactionId;
  final String senderId;
  final String receiverId;
  final double amount;
  final String channel;
  final String timestamp;
  final double riskScore;
  final Map<String, dynamic> raw;

  Transaction({
    required this.transactionId,
    required this.senderId,
    required this.receiverId,
    required this.amount,
    required this.channel,
    required this.timestamp,
    required this.riskScore,
    required this.raw,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      transactionId: json['transaction_id']?.toString() ??
          json['txn_id']?.toString() ?? '',
      senderId: json['sender_id']?.toString() ??
          json['sender_account']?.toString() ??
          json['from_account']?.toString() ?? '',
      receiverId: json['receiver_id']?.toString() ??
          json['receiver_account']?.toString() ??
          json['to_account']?.toString() ?? '',
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
      channel: json['channel']?.toString() ?? 'UPI',
      timestamp: json['timestamp']?.toString() ??
          json['created_at']?.toString() ?? '',
      riskScore: (json['risk_score'] as num?)?.toDouble() ?? 0.0,
      raw: json,
    );
  }

  String get channelEmoji {
    switch (channel.toUpperCase()) {
      case 'UPI':
        return '📱';
      case 'IMPS':
        return '🏦';
      case 'NEFT':
        return '🔄';
      case 'SALARY':
        return '💼';
      default:
        return '💳';
    }
  }

  String get formattedAmount {
    final b = amount.toInt();
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

  DateTime get parsedDateTime {
    if (timestamp.isEmpty) return DateTime.now();
    try {
      return DateTime.parse(timestamp).toLocal();
    } catch (_) {
      return DateTime.now();
    }
  }

  String get formattedTime {
    if (timestamp.isEmpty) return '--:--';
    try {
      final parsed = DateTime.parse(timestamp).toLocal();
      final hour = parsed.hour.toString().padLeft(2, '0');
      final minute = parsed.minute.toString().padLeft(2, '0');
      return '$hour:$minute';
    } catch (_) {
      final parts = timestamp.split(' ');
      final lastPart = parts.last.split('T').last;
      if (lastPart.length >= 5) {
        return lastPart.substring(0, 5);
      }
      return lastPart;
    }
  }
}
