class Investigation {
  final String investigationId;
  final String status;
  final double finalRiskScore;
  final String finalVerdict;
  final String explanationNarrative;
  final Map<String, dynamic> raw;

  Investigation({
    required this.investigationId,
    required this.status,
    required this.finalRiskScore,
    required this.finalVerdict,
    required this.explanationNarrative,
    required this.raw,
  });

  factory Investigation.fromJson(Map<String, dynamic> json) {
    return Investigation(
      investigationId: json['investigation_id']?.toString() ??
          json['id']?.toString() ?? '',
      status: json['status']?.toString() ?? 'pending',
      finalRiskScore: (json['final_risk_score'] as num?)?.toDouble() ?? 0.0,
      finalVerdict: json['final_verdict']?.toString() ?? '',
      explanationNarrative:
          json['explanation_narrative']?.toString() ?? '',
      raw: json,
    );
  }

  bool get isPending => status.toLowerCase() == 'pending';

  bool get isFraud =>
      finalRiskScore > 0.7 || finalVerdict.toUpperCase() == 'FRAUD';

  bool get isClean => finalRiskScore < 0.4;

  // isSuspicious: between 0.4 and 0.7
  bool get isSuspicious => !isFraud && !isClean;

  String get riskPercent =>
      '${(finalRiskScore * 100).toStringAsFixed(0)}%';
}
