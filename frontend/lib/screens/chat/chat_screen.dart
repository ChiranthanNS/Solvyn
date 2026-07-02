import 'package:flutter/material.dart';
import '../../services/api_service.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final ApiService api = ApiService.instance;
  final TextEditingController msgCtrl = TextEditingController();
  final ScrollController scrollCtrl = ScrollController();

  List<Map<String, String>> messages = [];
  bool sending = false;

  void scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 200), () {
      if (scrollCtrl.hasClients) {
        scrollCtrl.animateTo(
          scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> sendMessage() async {
    final text = msgCtrl.text.trim();
    if (text.isEmpty || sending) return;

    setState(() {
      messages.add({"sender": "user", "text": text});
      sending = true;
    });

    msgCtrl.clear();
    scrollToBottom();

    final reply = await api.aiChat(text);

    setState(() {
      messages.add({
        "sender": "ai",
        "text": reply ?? "No response from Solvyn",
      });
      sending = false;
    });

    scrollToBottom();
  }

  Widget chatBubble(String sender, String text) {
    final isUser = sender == "user";

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
        padding: const EdgeInsets.all(14),
        constraints: const BoxConstraints(maxWidth: 260),
        decoration: BoxDecoration(
          color: isUser ? Colors.deepPurple : Colors.grey.shade300,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: isUser ? Colors.white : Colors.black87,
            fontSize: 15,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Solvyn AI"),
        backgroundColor: Colors.deepPurple,
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: scrollCtrl,
              itemCount: messages.length,
              itemBuilder: (context, index) {
                final msg = messages[index];
                return chatBubble(
                  msg["sender"]!,
                  msg["text"]!,
                );
              },
            ),
          ),
          if (sending)
            const Padding(
              padding: EdgeInsets.all(8),
              child: Text("Solvyn is thinking..."),
            ),
          Container(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: msgCtrl,
                    decoration: const InputDecoration(
                      hintText: "Type a message...",
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send, color: Colors.deepPurple),
                  onPressed: sendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
