import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/chat_message.dart';
import '../services/chat_service.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<ChatMessage> _messages = [];
  final TextEditingController _controller = TextEditingController();
  bool _isLoading = true;
  bool _isSending = false;
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    try {
      final history = await ChatService.getHistory();
      if (mounted) {
        setState(() { _messages.addAll(history); _isLoading = false; });
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(e.toString()), backgroundColor: Colors.redAccent));
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(_scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300), curve: Curves.easeOutCubic);
      }
    });
  }

  Future<void> _sendMessage() async {
    if (_controller.text.trim().isEmpty) return;
    final text = _controller.text;
    _controller.clear();
    setState(() {
      _messages.add(ChatMessage(id: DateTime.now().millisecondsSinceEpoch, userId: 0, sender: 'user', message: text, timestamp: DateTime.now()));
      _isSending = true;
    });
    _scrollToBottom();
    try {
      final response = await ChatService.sendMessage(text);
      if (mounted) {
        setState(() {
          _messages.add(ChatMessage(id: DateTime.now().millisecondsSinceEpoch, userId: 0, sender: 'ai', message: response['reply'] ?? '', timestamp: DateTime.now()));
        });
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(e.toString()), backgroundColor: Colors.redAccent));
      }
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
            : ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.only(left: 16, right: 16, top: 16, bottom: 80),
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  final msg = _messages[index];
                  final isUser = msg.sender == 'user';
                  return Align(
                    alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                      decoration: BoxDecoration(
                        gradient: isUser
                          ? const LinearGradient(colors: [Color(0xFF00B4DB), Color(0xFF0083B0)])
                          : LinearGradient(colors: [Colors.white.withOpacity(0.15), Colors.white.withOpacity(0.05)]),
                        borderRadius: BorderRadius.only(
                          topLeft: const Radius.circular(24), topRight: const Radius.circular(24),
                          bottomLeft: isUser ? const Radius.circular(24) : const Radius.circular(4),
                          bottomRight: isUser ? const Radius.circular(4) : const Radius.circular(24),
                        ),
                        border: isUser ? null : Border.all(color: Colors.white.withOpacity(0.2)),
                        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 10, offset: const Offset(0, 4))],
                      ),
                      child: Text(msg.message, style: GoogleFonts.inter(fontSize: 15, color: Colors.white, height: 1.4)),
                    ).animate().slideY(begin: 0.2, duration: 400.ms, curve: Curves.easeOutCubic).fadeIn(),
                  );
                },
              ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(0.5),
            border: Border(top: BorderSide(color: Colors.white.withOpacity(0.1))),
          ),
          child: SafeArea(
            top: false,
            child: Row(
              children: [
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(30),
                      border: Border.all(color: Colors.white.withOpacity(0.2)),
                    ),
                    child: TextField(
                      controller: _controller,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: 'Message Solvyn...',
                        hintStyle: TextStyle(color: Colors.white.withOpacity(0.5)),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                      ),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Container(
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xFF00B4DB), Color(0xFF0083B0)]),
                    shape: BoxShape.circle,
                    boxShadow: [BoxShadow(color: const Color(0xFF00B4DB).withOpacity(0.4), blurRadius: 12, offset: const Offset(0, 4))],
                  ),
                  child: _isSending
                    ? const Padding(padding: EdgeInsets.all(12.0), child: SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)))
                    : IconButton(icon: const Icon(Icons.send_rounded, color: Colors.white), onPressed: _sendMessage),
                ),
              ],
            ),
          ),
        ).animate().slideY(begin: 1.0, duration: 500.ms, curve: Curves.easeOutCubic),
      ],
    );
  }
}
