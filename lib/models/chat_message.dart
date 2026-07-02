class ChatMessage {
  final int id;
  final int userId;
  final String sender;
  final String message;
  final DateTime timestamp;

  ChatMessage({
    required this.id,
    required this.userId,
    required this.sender,
    required this.message,
    required this.timestamp,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] ?? 0,
      userId: json['user_id'] ?? 0,
      sender: json['sender'] ?? 'unknown',
      message: json['message'] ?? '',
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'])
          : DateTime.now(),
    );
  }
}
