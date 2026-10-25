class DiaryEntry {
  final int id;
  final String? title;
  final String content;
  final String? mood;
  final String entryType;
  final DateTime createdAt;
  final DateTime? updatedAt;

  DiaryEntry({
    required this.id,
    this.title,
    required this.content,
    this.mood,
    this.entryType = 'user',
    required this.createdAt,
    this.updatedAt,
  });

  factory DiaryEntry.fromJson(Map<String, dynamic> json) {
    return DiaryEntry(
      id: json['id'] ?? 0,
      title: json['title'],
      content: json['content'] ?? '',
      mood: json['mood'],
      entryType: json['entry_type'] ?? 'user',
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
    );
  }
}
