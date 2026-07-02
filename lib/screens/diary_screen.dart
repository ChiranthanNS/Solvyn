import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/diary_entry.dart';
import '../services/diary_service.dart';

class DiaryScreen extends StatefulWidget {
  const DiaryScreen({super.key});
  @override
  State<DiaryScreen> createState() => _DiaryScreenState();
}

class _DiaryScreenState extends State<DiaryScreen> {
  final List<DiaryEntry> _entries = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadEntries();
  }

  Future<void> _loadEntries() async {
    try {
      final entries = await DiaryService.getEntries();
      if (mounted) {
        setState(() { _entries.clear(); _entries.addAll(entries.reversed); _isLoading = false; });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(e.toString()), backgroundColor: Colors.redAccent));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
          : _entries.isEmpty
              ? Center(
                  child: Text(
                    'No diary entries yet.\nSummaries of our conversations\nwill appear here automatically.',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.outfit(color: Colors.white54, fontSize: 18),
                  ).animate().fadeIn(delay: 400.ms),
                )
              : ListView.builder(
                  padding: const EdgeInsets.only(left: 16, right: 16, top: 24, bottom: 100),
                  itemCount: _entries.length,
                  itemBuilder: (context, index) {
                    final entry = _entries[index];
                    return Container(
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: Colors.white.withOpacity(0.15)),
                        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 15, offset: const Offset(0, 8))],
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: () {},
                            child: Padding(
                              padding: const EdgeInsets.all(20.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(entry.createdAt.toLocal().toString().split(' ')[0],
                                        style: GoogleFonts.outfit(color: Colors.cyanAccent, fontWeight: FontWeight.bold)),
                                      Text(entry.createdAt.toLocal().toString().split(' ')[1].substring(0, 5),
                                        style: GoogleFonts.inter(color: Colors.white54, fontSize: 12)),
                                    ],
                                  ),
                                  const SizedBox(height: 12),
                                  Text(entry.content, style: GoogleFonts.inter(color: Colors.white, fontSize: 15, height: 1.5)),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ).animate().slideY(begin: 0.1, delay: (50 * index).ms).fadeIn();
                  },
                ),
    );
  }
}
