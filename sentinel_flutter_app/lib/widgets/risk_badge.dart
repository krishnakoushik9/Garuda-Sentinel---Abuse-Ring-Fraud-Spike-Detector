import 'package:flutter/material.dart';
import '../models/account.dart';

class RiskBadge extends StatelessWidget {
  final Account account;
  const RiskBadge({super.key, required this.account});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: account.riskBadgeColor.withOpacity(0.2),
        borderRadius: BorderRadius.circular(50),
        border: Border.all(color: account.riskBadgeColor, width: 1),
      ),
      child: Text(
        account.riskBadgeLabel,
        style: TextStyle(
          color: account.riskBadgeColor,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
