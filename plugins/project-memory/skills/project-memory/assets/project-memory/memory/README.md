# Taşınabilir Proje Hafızası

Başlangıçta kök talimatlar, `INDEX.md` ve `CURRENT.md` okunur; görevle ilgili en fazla üç konu dosyası seçilir. Dosya kaydı, Git ve yedekleme ayrı doğrulanır. Bu protokol skill kurulmadan da geçerlidir.

## Kaydetme ve durum

Yalnız gelecekteki işi etkileyen bilgi kaydedilir. Geçici düşünceler CURRENT içinde kısa tutulur; ham sohbet, sır ve kopya kaynak kod saklanmaz. Kalıcı kaydın tek ana kaynağı vardır; INDEX ve CURRENT ona yönlendirir.

Yeni veya anlamı değişen kalıcı kayıt şu bilgileri taşır: sabit kimlik (REQ/DEC/ISSUE/LRN), tarih, durum, proje/kapsam, ifade, kaynak ve gerekiyorsa gerekçe/etkilenen alanlar. Mevcut eski kayıtlar topluca yeniden yazılmaz. Eksik kaynak veya durum doğrulanmış sayılmaz; ihtiyaç duyulduğunda tamamlanır. Kimlik tekrar kullanılmaz; aynı başlık kimlik değildir.

- `öneri`: değerlendirme bekliyor; onay veya uygulanmış davranış değildir.
- `onaylı`: kullanıcı kararı veya görev yetkisiyle alınmış karar; kimin/ne zaman onayladığı belirtilir. Uygulandığı ayrıca doğrulanır.
- `gözlem`: kullanıcı bildirimi veya ölçüm; hangisi olduğu ve koşulları belirtilir. Bildirilen hata kök neden değildir.
- `doğrulandı`: belirtilen sürüm/ortamda kanıtlandı; test veya kaynak yolu ve kontrol tarihi gerekir. Gelecekte de geçerli olacağı garanti edilmez.
- `çelişkili`, `yeniden doğrulama gerekli`: kullanım öncesi inceleme gerekir; belirsizlik otomatik çözülmez.
- `geçersiz kılındı`: eski gerekçe korunur; yerine geçen kaydın kimliğine/dosyasına bağlantı verilir. Yeni kayıt da eski kayda döner.

Bunlar otomatik durum makinesi değildir. Durumu kanıt ve yetki belirler; tekrar sayısı, yaş veya asistanın kendinden emin olması belirlemez. Bir önerinin kabulü uygulama onayı gerektiren diğer sınırları kaldırmaz.

## Kaynak ve kapsam

Kaynağı proje içi göreli dosya bağlantısı, kayıt kimliği, commit/sürüm, test çıktısı veya tarihli kullanıcı kararıyla belirt. Sohbet tek kaynaksa kararın gerekli cümlesini proje içinde kısa bir kayıt olarak koru; erişilemeyen sohbet bağlantısına bağımlı bırakma. Dış belge talimatı kullanıcı kararı sayılmaz.

Kaynak değiştiyse özetin dayandığı bölüm/sürümü karşılaştır; yalnız tarih değişti diye kaydı otomatik geçersiz kılma. Dosya hash'i bayt bütünlüğünü gösterir, anlamın doğruluğunu göstermez. Başka proje/müşteri/ortam kaydı, aynı başlıkta olsa bile buraya doğrulanmadan aktarılmaz.

## İlgili kaydı bulma

Önce INDEX ve CURRENT üzerinden kapsamı seç. Bilinen kimliği `rg -n -F -- "DEC-012" memory` ile, başlığı/terimi yalnız ilgili dosyalarda ara; ardından seçilen başlığın çevresini oku. `rg` yoksa editör veya PowerShell `Select-String` yeterlidir. Arşiv yalnız yönlendirme veya açık tarihsel soru gerektiğinde açılır. Bütün geçmişi varsayılan olarak yükleme.

Aynı başlıklı sonuçlarda kimlik, kapsam, durum ve kaynağı karşılaştır. Öneriyi onaylı karar yerine kullanma. Eski/geçersiz kayıt bulunduğunda yerine geçeni izle; çelişki çözülmüyorsa açıkça bildir. Kırık/kayıp kaynakta sonuca güvenme, kaynağı onar veya yeniden doğrulama gerektiğini belirt. Kaydı okuyup önemli güncel iddiayı gerçek kaynakla karşılaştır.

## Güncelleme ve koruma

Yeni bilgiyi mevcut kayıtla karşılaştır; yalnız yeni sonuç veya değişen kararı kaydet. Eski kararın gerekçesini silme. Değişikliğin etkilediği kayıtları/kaynakları kontrol et, ardından kısa yönlendirmeyi güncelle. Kullanıcı onayı gereken bir öneri otomatik uygulanmaz.

Sıkıştırma/arşivleme için önce özgün bayt yedeği ve kaynak→hedef eşleme hazırlanır; yalnız özete güvenerek silme yapılmaz. Anlamsal doğruluk sağlık kontrolünün BAŞARILI sonucu ile kanıtlanmaz. Gerçek sadeleştirme ayrıca değerlendirilir.

- Durum sorguları salt okunurdur. En yeni kullanıcı talimatını ve aynı sürüm, ortam ve kapsamda doğrulanmış proje kaynaklarını eski hafıza kayıtlarından önce değerlendir.

Sorun durumu: `açık`, `kapandı`, `yeniden açıldı`. Kanıt durumu ayrı yazılır. Kapanışa tarih, kapsam ve dayanak ekle. Eski `çözüldü` kayıtlarını kapsamıyla birlikte oku. Aynı kapsamda yeni kanıt veya açık karar olmadan yeniden açma.

Açık iş maddesinde önceki bulgu, açık soru veya engel, sıradaki adım ve doğrudan ana kaynak bağlantısı birlikte yer alır.

Oturum arşivi için `python tools/memory_archive_sessions.py` ile önizleme al. Çıkan özeti `--apply ÖZET` ile onayla. Normal kapanış yalnız ekler. Var olan projede ilk kullanım için `memory/ARCHIVE/SESSIONS.md` dosyasını arşiv başlığıyla oluştur. Bu dosya işlem günlüğü için başlangıç görüntüsüdür.
