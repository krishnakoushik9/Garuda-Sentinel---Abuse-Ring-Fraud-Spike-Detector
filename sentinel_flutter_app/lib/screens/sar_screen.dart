import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import 'package:share_plus/share_plus.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import '../models/investigation.dart';
import '../models/account.dart';

class SarScreen extends StatefulWidget {
  final Investigation investigation;
  final Account sender;
  final String txnId;
  final String amount;

  const SarScreen({
    super.key,
    required this.investigation,
    required this.sender,
    required this.txnId,
    required this.amount,
  });

  @override
  State<SarScreen> createState() => _SarScreenState();
}

class _SarScreenState extends State<SarScreen> {
  bool _filing = false;

  Future<void> _exportPdf() async {
    final inv = widget.investigation;
    final pdf = pw.Document();

    pdf.addPage(
      pw.MultiPage(
        theme: pw.ThemeData.withFont(
          base: await PdfGoogleFonts.nunitoRegular(),
          bold: await PdfGoogleFonts.nunitoBold(),
        ),
        build: (ctx) => [
          pw.Header(
            level: 0,
            child: pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Text('SUSPICIOUS ACTIVITY REPORT',
                    style: pw.TextStyle(
                        fontSize: 20,
                        fontWeight: pw.FontWeight.bold,
                        color: PdfColors.red700)),
                pw.Text('Bank of India — Fraud Intelligence Platform',
                    style: const pw.TextStyle(
                        fontSize: 12, color: PdfColors.grey600)),
                pw.SizedBox(height: 4),
                pw.Text(
                    'Generated: ${DateTime.now().toIso8601String()}',
                    style: const pw.TextStyle(
                        fontSize: 10, color: PdfColors.grey500)),
              ],
            ),
          ),
          pw.SizedBox(height: 16),

          _pdfSection('ACCOUNT INFORMATION', [
            _pdfRow('Account ID', widget.sender.accountId),
            _pdfRow('Customer Name', widget.sender.customerName),
            _pdfRow('Risk Profile', widget.sender.riskProfile),
          ]),

          _pdfSection('TRANSACTION DETAILS', [
            _pdfRow('Transaction ID', widget.txnId),
            _pdfRow('Amount', '₹${widget.amount}'),
            _pdfRow('Timestamp', DateTime.now().toIso8601String()),
            _pdfRow('Investigation ID', inv.investigationId),
          ]),

          _pdfSection('RISK ASSESSMENT', [
            _pdfRow('Final Verdict', inv.finalVerdict),
            _pdfRow('Risk Score', inv.riskPercent),
            _pdfRow('Status', inv.status),
          ]),

          _pdfSection('RISK INDICATORS', [
            pw.Text(inv.explanationNarrative,
                style: const pw.TextStyle(fontSize: 11)),
          ]),

          _pdfSection('RECOMMENDED ACTION', [
            pw.Text(
              inv.isFraud
                  ? 'BLOCK transaction and file with FIU-IND immediately. Freeze account pending investigation.'
                  : inv.isSuspicious
                      ? 'Flag for enhanced monitoring. Request documentation from account holder.'
                      : 'Allow transaction. Continue standard monitoring.',
              style: const pw.TextStyle(fontSize: 11),
            ),
          ]),
        ],
      ),
    );

    final bytes = await pdf.save();
    try {
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/SAR_${widget.txnId}.pdf');
      await file.writeAsBytes(bytes);
      await Share.shareXFiles(
        [XFile(file.path)],
        subject: 'SAR Report — ${widget.txnId}',
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Export error: $e')),
        );
      }
    }
  }

  pw.Widget _pdfSection(String title, List<pw.Widget> children) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.SizedBox(height: 12),
        pw.Text(title,
            style: pw.TextStyle(
                fontSize: 13,
                fontWeight: pw.FontWeight.bold,
                color: PdfColors.blueGrey800)),
        pw.Divider(),
        ...children,
        pw.SizedBox(height: 8),
      ],
    );
  }

  pw.Widget _pdfRow(String label, String value) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(vertical: 3),
      child: pw.Row(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.SizedBox(
            width: 140,
            child: pw.Text(label,
                style: const pw.TextStyle(
                    color: PdfColors.grey600, fontSize: 11)),
          ),
          pw.Expanded(
            child: pw.Text(value,
                style: const pw.TextStyle(fontSize: 11)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final inv = widget.investigation;
    return Scaffold(
      backgroundColor: const Color(0xFFF2F2F7), // systemBackground F2F2F7
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        scrolledUnderElevation: 0,
        leading: IconButton(
          icon: const Icon(CupertinoIcons.clear, color: Color(0xFF000000)), // Monochrome clear button
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          'SAR Report',
          style: TextStyle(
            fontFamily: 'SF Pro Display',
            color: Colors.black,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: SingleChildScrollView(
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top visual card header
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFE5E5EA), width: 0.5),
              ),
              child: Column(
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      color: const Color(0xFFFF3B30).withOpacity(0.08),
                      shape: BoxShape.circle,
                    ),
                    child: const Center(
                      child: Text('🏛️', style: TextStyle(fontSize: 32)),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'SUSPICIOUS ACTIVITY REPORT',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: 'SF Pro Display',
                      color: Color(0xFFFF3B30),
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.0,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Bank of India — Fraud Intelligence Platform',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: 'SF Pro Text',
                      color: Color(0xFF8E8E93),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            _section('Account Information', [
              _row('Account ID', widget.sender.accountId),
              _row('Customer Name', widget.sender.customerName),
              _row('Risk Profile', widget.sender.riskProfile),
            ]),

            _section('Transaction Details', [
              _row('Transaction ID', widget.txnId),
              _row('Amount', '₹${widget.amount}'),
              _row('Timestamp', DateTime.now().toString().substring(0, 19)),
              _row('Investigation ID', inv.investigationId),
            ]),

            _section('Risk Assessment', [
              _row('Final Verdict', inv.finalVerdict),
              _riskScoreRow(inv),
              _row('Status', inv.status.toUpperCase()),
            ]),

            _section('Risk Indicators', [
              const SizedBox(height: 4),
              Text(
                inv.explanationNarrative.isNotEmpty
                    ? inv.explanationNarrative
                    : 'No narrative available.',
                style: const TextStyle(
                  fontFamily: 'SF Pro Text',
                  color: Colors.black87,
                  fontSize: 14,
                  height: 1.5,
                ),
              ),
            ]),

            // SHAP values if present
            if (inv.raw.containsKey('shap_values'))
              _section('ML Evidence (SHAP)', [
                Text(
                  inv.raw['shap_values'].toString(),
                  style: const TextStyle(
                    fontFamily: 'monospace',
                    color: Color(0xFF6E6E73),
                    fontSize: 12,
                  ),
                ),
              ]),

            _section('Recommended Action', [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFF3B30).withOpacity(0.08),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFFF3B30).withOpacity(0.3), width: 0.5),
                ),
                child: Text(
                  inv.isFraud
                      ? 'BLOCK transaction. Freeze account pending investigation. File with FIU-IND within 7 days.'
                      : inv.isSuspicious
                          ? 'Flag for enhanced monitoring. Request documentation from account holder.'
                          : 'Allow transaction. Continue standard monitoring.',
                  style: const TextStyle(
                    fontFamily: 'SF Pro Text',
                    color: Color(0xFFFF3B30),
                    fontSize: 14,
                    height: 1.4,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ]),

            const SizedBox(height: 32),

            // Export PDF button (Pill shape, #000000 filled background)
            SizedBox(
              width: double.infinity,
              height: 50,
              child: CupertinoButton(
                padding: EdgeInsets.zero,
                color: const Color(0xFF000000), // Monochrome black action
                borderRadius: BorderRadius.circular(25),
                onPressed: _exportPdf,
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.picture_as_pdf_outlined, color: Colors.white, size: 20),
                    SizedBox(width: 8),
                    Text(
                      'Export PDF Report',
                      style: TextStyle(
                        fontFamily: 'SF Pro Rounded',
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),

            // File with FIU-IND (Alert / Destructive color #FF3B30 primary action)
            SizedBox(
              width: double.infinity,
              height: 50,
              child: CupertinoButton(
                padding: EdgeInsets.zero,
                color: const Color(0xFFFF3B30), // Destructive/alert red filled button
                borderRadius: BorderRadius.circular(25),
                onPressed: _filing
                    ? null
                    : () async {
                        setState(() => _filing = true);
                        await Future.delayed(const Duration(seconds: 2));
                        setState(() => _filing = false);
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Row(
                                children: [
                                  Icon(CupertinoIcons.checkmark_seal_fill, color: Colors.white),
                                  SizedBox(width: 8),
                                  Text('SAR Filed Successfully with FIU-IND'),
                                ],
                              ),
                              backgroundColor: Color(0xFF000000), // Monochrome black snackbar
                              behavior: SnackBarBehavior.floating,
                            ),
                          );
                          Navigator.pop(context);
                        }
                      },
                child: Center(
                  child: _filing
                      ? const CupertinoActivityIndicator(color: Colors.white)
                      : const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.gavel, color: Colors.white, size: 20),
                            SizedBox(width: 8),
                            Text(
                              'File with FIU-IND',
                              style: TextStyle(
                                fontFamily: 'SF Pro Rounded',
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ],
                        ),
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _section(String title, List<Widget> children) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 20),
        Padding(
          padding: const EdgeInsets.only(left: 4.0),
          child: Text(
            title.toUpperCase(),
            style: const TextStyle(
              fontFamily: 'SF Pro Text',
              color: Color(0xFF8E8E93),
              fontSize: 12,
              fontWeight: FontWeight.bold,
              letterSpacing: 0.5,
            ),
          ),
        ),
        const SizedBox(height: 8),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFE5E5EA), width: 0.5),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: children,
          ),
        ),
      ],
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: const TextStyle(
                fontFamily: 'SF Pro Text',
                color: Color(0xFF8E8E93),
                fontSize: 14,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontFamily: 'SF Pro Text',
                color: Colors.black,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _riskScoreRow(Investigation inv) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          const SizedBox(
            width: 130,
            child: Text(
              'Risk Score',
              style: TextStyle(
                fontFamily: 'SF Pro Text',
                color: Color(0xFF8E8E93),
                fontSize: 14,
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFFFF3B30).withOpacity(0.08),
              borderRadius: BorderRadius.circular(50),
              border: Border.all(color: const Color(0xFFFF3B30).withOpacity(0.3), width: 0.5),
            ),
            child: Text(
              inv.riskPercent,
              style: const TextStyle(
                fontFamily: 'SF Pro Text',
                color: Color(0xFFFF3B30),
                fontWeight: FontWeight.bold,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
