import 'package:flutter/material.dart';
import '../../services/api_service.dart';

class DiaryWriteScreen extends StatefulWidget {
  const DiaryWriteScreen({super.key});

  @override
  State<DiaryWriteScreen> createState() => _DiaryWriteScreenState();
}

class _DiaryWriteScreenState extends State<DiaryWriteScreen> {
  final ApiService api = ApiService.instance;
  final TextEditingController textCtrl = TextEditingController();
  bool saving = false;

  Future<void> saveDiary() async {
    final text = textCtrl.text.trim();
    if (text.isEmpty) return;

    setState(() => saving = true);

    final success = await api.createDiary(text);

    setState(() => saving = false);

    if (success) {
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Failed to save diary")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Write Diary"),
        backgroundColor: Colors.deepPurple,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Expanded(
              child: TextField(
                controller: textCtrl,
                maxLines: null,
                expands: true,
                decoration: const InputDecoration(
                  hintText: "Write your thoughts...",
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: saving ? null : saveDiary,
              child: saving
                  ? const CircularProgressIndicator()
                  : const Text("Save"),
            ),
          ],
        ),
      ),
    );
  }
}
