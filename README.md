# Replit Kullanım Talimatları

Bu proje Replit üzerinde çalıştırılabilir. Aşağıdaki komutlar, projeyi başlatmak ve yönetmek için kullanılabilir:

- **Projeyi Başlatmak:**
  ```bash
  python3 sinyal.py
  ```
  Bu komut, ana Python uygulamasını başlatır.

- **Bağımlılıkları Yüklemek:**
  Replit, `replit.nix` dosyasında belirtilen bağımlılıkları otomatik olarak yükler. Ancak, herhangi bir sorun yaşarsanız, aşağıdaki adımları izleyebilirsiniz:

  1. Nix kabuğunu etkinleştirin:
     ```bash
     nix-shell
     ```

  2. Bağımlılıkları yükleyin (gerekli olmayabilir, Replit otomatik olarak yapar):
     ```bash
     # Bu adım genellikle gerekli değildir, Replit otomatik olarak yapar
     ```

- **Proje Ortamını Güncellemek:**
  `replit.nix` dosyasında değişiklik yaptıktan sonra, ortamı güncellemek için Replit'i yeniden başlatmanız yeterlidir.

- **Gizli Değişkenleri Ayarlamak:**
  Replit, gizli değişkenleri (secrets) ayarlamanıza olanak tanır. Bu değişkenler, kodunuzda güvenli bir şekilde kullanılabilir. Örneğin:
  - `TELEGRAM_TOKEN`: Telegram bot token'ı
  - `GEMINI_API_KEY`: Gemini API anahtarı

  Bu değişkenleri Replit arayüzünden ayarlayabilirsiniz.

- **Projeyi Durdurmak:**
  Replit arayüzünden projeyi durdurabilirsiniz.

Bu talimatlar, projenizi Replit üzerinde sorunsuz bir şekilde çalıştırmanıza yardımcı olacaktır.
