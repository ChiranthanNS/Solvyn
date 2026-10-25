import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:solvyn/main.dart';
import 'package:solvyn/providers/auth_provider.dart';

void main() {
  testWidgets('Solvyn opens on the private diary sign-in screen', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AuthProvider()),
        ],
        child: const MyApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Solvyn'), findsOneWidget);
    expect(find.text('Your private diary and reflection space.'), findsOneWidget);
    expect(find.text('Login'), findsOneWidget);
  });
}
