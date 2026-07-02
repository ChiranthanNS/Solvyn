class DiaryEntry {
  final int id;
  final String content;
  final DateTime createdAt;

  DiaryEntry({
    required this.id,
    required this.content,
    required this.createdAt,
  });

  factory DiaryEntry.fromJson(Map<String, dynamic> json) {
    return DiaryEntry(
      id: json['id'] ?? 0,
      content: json['content'] ?? '',
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
    );
  }
}
