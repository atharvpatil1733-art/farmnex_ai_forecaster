// CEDA credit. REQUIRED by CEDA's terms on every screen that shows these prices:
// their logo at the bottom right + the text credit. Copy to lib/widgets/ceda_credit.dart.
//
// 1. Download the official CEDA logo from https://ceda.ashoka.edu.in/api-terms-conditions/
//    and save it as assets/images/ceda_logo.png
// 2. In pubspec.yaml under `flutter:` add:
//        assets:
//          - assets/images/ceda_logo.png

import 'package:flutter/material.dart';

class CedaCredit extends StatelessWidget {
  const CedaCredit({super.key, required this.text});

  /// Pass meta['attribution'] (or any forecast answer's 'attribution') from the API.
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end, // bottom RIGHT, as CEDA requires
        children: [
          Flexible(
            child: Text(text,
                textAlign: TextAlign.right,
                style: Theme.of(context).textTheme.bodySmall),
          ),
          const SizedBox(width: 8),
          Image.asset('assets/images/ceda_logo.png', height: 28),
        ],
      ),
    );
  }
}
