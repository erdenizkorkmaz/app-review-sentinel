# App Review Sentinel

Mobil uygulama yorumlarını takip eden, negatif yorumları tespit edip bildiren otomasyon.

## Özellikler

- **App Store** yorumlarını çekme (RSS API)
- **Sentiment analizi** (rating + keyword bazlı)
- **Negatif yorum alertleri** (Slack/Discord webhook)
- **Daha önce görülen yorumları filtreleme**
- **GitHub Actions** ile otomatik çalışma

## Kurulum

### 1. Repository Secrets Ayarla

GitHub repo ayarlarında şu secrets'ları ekle:

| Secret | Açıklama | Örnek |
|--------|----------|-------|
| `APP_CONFIGS` | Takip edilecek uygulamalar | `MyApp:1234567890:com.example.app` |
| `WEBHOOK_URL` | Slack/Discord webhook URL | `https://hooks.slack.com/...` |

### APP_CONFIGS Format

```
app_name:ios_app_id:android_package
```

Birden fazla uygulama için virgülle ayır:

```
MyApp:1234567890:com.example.app,OtherApp:9876543210:com.other.app
```

### 2. Manuel Çalıştırma

```bash
export APP_CONFIGS="MyApp:1234567890:com.example.app"
export WEBHOOK_URL="https://hooks.slack.com/services/..."
python app_review_sentinel.py
```

## App Store App ID Bulma

1. App Store'da uygulamayı aç
2. Share > Copy Link
3. URL'den ID'yi al: `https://apps.apple.com/us/app/id1234567890`

## Google Play Setup

Google Play için `google-play-scraper` paketi gereklidir. Şu an için sadece App Store desteği tam çalışmaktadır.

## Çalışma Sıklığı

Varsayılan: Her 4 saatte bir

`.github/workflows/automation.yml` dosyasından değiştirebilirsiniz:

```yaml
schedule:
  - cron: '0 */4 * * *'  # Her 4 saat
```

## License

MIT
