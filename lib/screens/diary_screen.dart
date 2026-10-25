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
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadEntries();
  }

  Future<void> _loadEntries() async {
    try {
      final entries = await DiaryService.getEntries();
      if (mounted) {
        setState(() {
          _entries
            ..clear()
            ..addAll(entries);
          _isLoading = false;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = e.toString();
        });
      }
    }
  }

  Future<void> _showEntryEditor({DiaryEntry? entry}) async {
    final controller = TextEditingController(text: entry?.content ?? '');
    final formKey = GlobalKey<FormState>();
    var isSaving = false;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(entry == null ? 'Write a diary entry' : 'Edit diary entry'),
          content: Form(
            key: formKey,
            child: TextFormField(
              controller: controller,
              autofocus: true,
              minLines: 5,
              maxLines: 10,
              maxLength: 6000,
              decoration: const InputDecoration(
                hintText: 'Write what you would like to remember…',
                border: OutlineInputBorder(),
              ),
              validator: (value) => value == null || value.trim().isEmpty
                  ? 'Write a few words before saving.'
                  : null,
            ),
          ),
          actions: [
            TextButton(
              onPressed: isSaving ? null : () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: isSaving
                  ? null
                  : () async {
                      if (!formKey.currentState!.validate()) return;
                      setDialogState(() => isSaving = true);
                      try {
                        if (entry == null) {
                          await DiaryService.createEntry(controller.text.trim());
                        } else {
                          await DiaryService.updateEntry(
                            entry.id,
                            controller.text.trim(),
                          );
                        }
                        if (!mounted) return;
                        Navigator.pop(dialogContext);
                        await _loadEntries();
                        if (mounted) {
                          ScaffoldMessenger.of(this.context).showSnackBar(
                            SnackBar(
                              content: Text(
                                entry == null ? 'Entry saved.' : 'Entry updated.',
                              ),
                            ),
                          );
                        }
                      } catch (error) {
                        setDialogState(() => isSaving = false);
                        if (mounted) {
                          ScaffoldMessenger.of(this.context).showSnackBar(
                            SnackBar(
                              content: Text('Could not save entry: $error'),
                              backgroundColor: Colors.redAccent,
                            ),
                          );
                        }
                      }
                    },
              child: Text(isSaving ? 'Saving…' : 'Save'),
            ),
          ],
        ),
      ),
    );
    controller.dispose();
  }

  Future<void> _deleteEntry(DiaryEntry entry) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Delete this entry?'),
        content: const Text('This entry will be permanently deleted.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await DiaryService.deleteEntry(entry.id);
      if (mounted) {
        setState(() => _entries.removeWhere((saved) => saved.id == entry.id));
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Entry deleted.')),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not delete entry: $error'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'Your diary could not load.',
                          style: TextStyle(color: Colors.white, fontSize: 17),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _error!,
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: Colors.white70),
                        ),
                        const SizedBox(height: 12),
                        OutlinedButton(
                          onPressed: _loadEntries,
                          child: const Text('Try again'),
                        ),
                      ],
                    ),
                  ),
                )
          : _entries.isEmpty
              ? Center(
                  child: Text(
                    'Your diary is ready when you are.\nWrite a thought or moment you want to keep.',
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
                                       Row(
                                         mainAxisSize: MainAxisSize.min,
                                         children: [
                                           Text(entry.createdAt.toLocal().toString().split(' ')[1].substring(0, 5),
                                             style: GoogleFonts.inter(color: Colors.white54, fontSize: 12)),
                                           IconButton(
                                             tooltip: 'Edit entry',
                                             onPressed: () => _showEntryEditor(entry: entry),
                                             icon: const Icon(Icons.edit_outlined, size: 18, color: Colors.white70),
                                           ),
                                           IconButton(
                                             tooltip: 'Delete entry',
                                             onPressed: () => _deleteEntry(entry),
                                             icon: const Icon(Icons.delete_outline, size: 18, color: Colors.white70),
                                           ),
                                         ],
                                       ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),
                                  Text(entry.content, style: GoogleFonts.inter(color: Colors.white, fontSize: 15, height: 1.5)),
                                ],
                              ),
                             ),
                        ),
                      ),
                    ).animate().slideY(begin: 0.1, delay: (50 * index).ms).fadeIn();
                  },
                ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showEntryEditor,
        icon: const Icon(Icons.edit_note),
        label: const Text('Write entry'),
      ),
    );
  }
}
