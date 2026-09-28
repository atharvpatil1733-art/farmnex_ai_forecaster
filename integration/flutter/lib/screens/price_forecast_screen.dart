// Example screen: pick market + crop, see the next 3 days' prices. Copy to
// lib/screens/price_forecast_screen.dart and open it with:
//   Navigator.push(context, MaterialPageRoute(builder: (_) => PriceForecastScreen(api: api)));
// Use it as a pattern for the demand, sell-options and crop screens.

import 'package:flutter/material.dart';

import '../services/forecast_api.dart';
import '../widgets/ceda_credit.dart';

class PriceForecastScreen extends StatefulWidget {
  const PriceForecastScreen({super.key, required this.api});
  final ForecastApi api;

  @override
  State<PriceForecastScreen> createState() => _PriceForecastScreenState();
}

class _PriceForecastScreenState extends State<PriceForecastScreen> {
  Map<String, dynamic>? meta;
  Map<String, dynamic>? forecast;
  String? market;
  String? crop;
  String? error;
  bool loading = false;

  @override
  void initState() {
    super.initState();
    widget.api.getMeta().then((m) => setState(() => meta = m)).catchError(
        (e) => setState(() => error = '$e'));
  }

  /// Crops available at the chosen market (from meta['markets'][i]['crops']).
  List<String> _cropsFor(String? m) {
    final markets = (meta?['markets'] as List? ?? []);
    final hit = markets.cast<Map>().where((x) => x['market'] == m);
    return hit.isEmpty ? [] : List<String>.from(hit.first['crops'] as List);
  }

  Future<void> _load() async {
    if (market == null || crop == null) return;
    setState(() { loading = true; error = null; });
    try {
      final f = await widget.api.getPriceForecast(market!, crop!);
      setState(() => forecast = f);
    } catch (e) {
      setState(() => error = '$e');
    } finally {
      setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final markets = (meta?['markets'] as List? ?? []).map((m) => m['market'] as String).toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Mandi price forecast')),
      body: meta == null && error == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              DropdownButton<String>(
                hint: const Text('Choose market'),
                value: market,
                isExpanded: true,
                items: markets.map((m) => DropdownMenuItem(value: m, child: Text(m))).toList(),
                onChanged: (v) => setState(() { market = v; crop = null; forecast = null; }),
              ),
              DropdownButton<String>(
                hint: const Text('Choose crop'),
                value: crop,
                isExpanded: true,
                items: _cropsFor(market).map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                onChanged: (v) { setState(() => crop = v); _load(); },
              ),
              if (loading) const Padding(padding: EdgeInsets.all(16), child: LinearProgressIndicator()),
              if (error != null) Text(error!, style: const TextStyle(color: Colors.red)),
              if (forecast != null) ...[
                Text('Based on mandi data up to ${forecast!['as_of']}',
                    style: Theme.of(context).textTheme.bodySmall),
                for (final d in forecast!['days'] as List)
                  Card(
                    child: ListTile(
                      title: Text('${d['date']}: about Rs ${(d['p50'] as num).round()} / quintal'),
                      subtitle: Text('Likely between Rs ${(d['p10'] as num).round()} and '
                          'Rs ${(d['p90'] as num).round()}'
                          '${d['likely_closed'] == true ? '  (market usually closed)' : ''}'),
                    ),
                  ),
                const SizedBox(height: 8),
                const Text('Why:', style: TextStyle(fontWeight: FontWeight.bold)),
                for (final r in forecast!['reason'] as List) Text('• $r'),
              ],
            ]),
      bottomNavigationBar: CedaCredit(text: (meta?['attribution'] ?? '') as String),
    );
  }
}
