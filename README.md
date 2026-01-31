## Algo-Trade-Backtester (v8.39)
Bu proje, volatil varlıklarda (BIST:AKFYE vb.) trend takibi ve dinamik tahliye senaryolarını test etmek amacıyla geliştirilmiş bir backtest algoritmasıdır.

## Teknik Altyapı ve İndikatör Seçimi
Algoritma, rastgele sinyaller yerine birbiriyle mutabık çalışan hiyerarşik bir onay mekanizması üzerine kurulmuştur:
EMA 50 & Slope: Ana trend yönü belirlenir; sadece eğimi pozitif ve fiyatın EMA üzerindeki %0.33'lük (1.0033) bölgede olduğu durumlar "Kral Şartı" olarak kabul edilir.
Hacim Teyidi: Alım sinyallerinin geçerli olması için anlık hacmin 20 günlük ortalamanın üzerinde olması (para girişi) şarttır.
Bollinger Üst Band Filtresi: Fiyatın istatistiksel olarak "aşırı pahalı" (Upper Band) olduğu bölgelerde alım baskılanarak tepe maliyet riskleri minimize edilir.
SuperTrend: Trendin yataylaştığı veya negatif olduğu bölgelerde filtreleme yaparak "tester piyasası" kayıplarını engeller.

## Dinamik Tahliye Mekanizmaları
Sıradan stop-loss mantığının aksine, bu sürümde piyasa yorgunluğunu ölçen özel tahliye filtreleri uygulanmıştır:
Hassas Tahliye (%34.7): Mum gövdesinin toplam mum boyuna oranının %34.7'yi aştığı ardışık 4 kırmızı günde, trend kırılmasa dahi güçlü satış baskısı nedeniyle pozisyon kapatılır.
Kesin Tahliye: Piyasa momentumunun tamamen kaybolduğu 5 günlük kırmızı seride koşulsuz çıkış yapılır.
Zirve Fitil Kontrolü: Bollinger üst bandına yakın bölgelerde oluşan 2.5x gövde-fitil oranlı mumlar "satış baskısı" olarak yorumlanır ve ceza moduna geçilir.

Kurulum ve Kullanım
Kütüphane bağımlılıklarını yüklemek için:

```bash
pip install -r requirements.txt
Simülasyonu başlatmak için:

```bash
python main.py
```
Sonuç
Strateji, AKFYE 2023-2026 verilerinde 10.000 TL başlangıç sermayesini, disiplinli tahliye yöntemleri sayesinde 21.602,20 TL seviyesine ulaştırmıştır.

## Performans Analizi ve Son Not
Bu algoritma, ilk işlem tarihinden 30.01.2026 tarihine kadar olan süreçte test edilmiştir. Söz konusu dönemde baz alınan hisse (AKFYE) yaklaşık %60 oranında değer kazanırken; geliştirilen strateji, disiplinli giriş-çıkış mekanizmaları sayesinde bu getiriyi yaklaşık ikiye katlayarak başlangıç sermayesini %116 oranında artırmıştır.
Bu sonuçlar, algoritmanın sadece trend takibi yapmakla kalmayıp, piyasadaki sert satış baskılarını önceden tespit ederek sermaye koruma (capital preservation) hedefine ulaştığını kanıtlamaktadır.
Kodlama yalnızca AKFYE hissesine özel yazılmıştır, her hissenin karakteri farklıdır. GÜN GEÇTİKÇE GÜNCELLENECEKTİR

## YASAL UYARI: Burada yer alan tüm kodlar, analizler ve backtest sonuçları sadece eğitim amaçlıdır. Geçmiş performans, gelecekteki sonuçların garantisi olamaz. Bu içerik hiçbir şekilde yatırım tavsiyesi niteliği taşımamaktadır. Yapılacak tüm işlemlerin sorumluluğu kullanıcıya aittir.