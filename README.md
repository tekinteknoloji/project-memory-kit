# Project Memory Kit

Codex ve diğer yapay zekâ araçları için proje klasöründe yaşayan, taşınabilir ve token-verimli Markdown hafızası.

## Özellikler

- Proje başına kendi kendine yeterli Markdown hafızası
- Yalnızca gerekli bağlamı yükleyerek düşük token kullanımı
- Gereksinim, karar, mimari, sorun ve öğrenimlerin ayrı tutulması
- Sağlık kontrolü ve doğrulanmış oturum kapanış makbuzu
- Windows'ta tek tık kurulum, yedekli güncelleme ve kaldırma
- Codex skill, yerel plugin ve sağlayıcıdan bağımsız proje şablonu

## Arkadaşına gönderme

Bu klasörün tamamını ZIP olarak gönderin veya bir Git deposunda paylaşın. Paket kişisel proje hafızası, parola, API anahtarı ya da makineye özel ayar içermez.

## Tek tıkla Windows kurulumu

1. ZIP dosyasını bir klasöre çıkarın.
2. `PROJECT-MEMORY-KUR.cmd` dosyasına çift tıklayın.
3. `KURULUM BASARILI` mesajından sonra Codex'i yeniden başlatın veya yeni bir görev açın.

Windows bir güvenlik uyarısı gösterirse dosyanın bu paket içinden geldiğini doğrulayın. Kurucu yönetici yetkisi istemez; yalnızca mevcut kullanıcının `.codex` klasörüne kurulum yapar.

Önceden kurulu sürümü güncellemek için `PROJECT-MEMORY-GUNCELLE.cmd`, kaldırmak için `PROJECT-MEMORY-KALDIR.cmd` dosyasına çift tıklayın.

## PowerShell ile gelişmiş kurulum

PowerShell'i bu klasörde açın ve çalıştırın:

```powershell
.\install.ps1 -InstallGlobalRules
```

`-InstallGlobalRules`, yeni ve kapsamlı projelerde hafızanın otomatik başlatılmasını sağlar. Yalnızca skill kurulacaksa bu parametreyi kullanmayın. Var olan kurulum güncellenirken `-Force` önceki skill'i zaman damgalı bir klasöre yedekler.

Kurulumdan sonra Codex'te yeni bir görev açın ve şunu yazın:

```text
$project-memory skill'ini kullan. Bu projede taşınabilir hafızayı başlat ve sağlık kontrolü yap.
```

## Codex plugin olarak kurulum

Bu depo aynı zamanda yerel bir Codex marketplace içerir. Marketplace kökü bu klasördür:

```powershell
codex plugin marketplace add .
codex plugin add project-memory@personal
```

Ardından yeni bir Codex görevi açın. Codex CLI sürümünüz plugin komutlarını desteklemiyorsa `install.ps1` yöntemi bağımsız olarak çalışır.

## Başka yapay zekâlarda kullanım

Skill zorunlu değildir. `plugins/project-memory/skills/project-memory/assets/project-memory/` şablonunu yeni proje klasörüne kopyalayın. Yapay zekâya önce kök `AGENTS.md`, sonra `memory/INDEX.md` ve `memory/CURRENT.md` dosyalarını okumasını söyleyin.

## Kaldırma

```powershell
.\uninstall.ps1 -RemoveGlobalRules
```

Kaldırma betiği yalnızca kurulu `project-memory` skill klasörünü ve işaretlenmiş global kural bloğunu hedefler. Global dosya değiştirilmeden önce yedeklenir.

## Doğrulama

Depo testlerinin tamamı:

```powershell
python -m unittest discover -s tests -p "test_*.py"
.\tests\test_one_click.ps1
.\tests\test_safety.ps1
```

GitHub Actions, her push ve pull request için paket testlerini Windows ve Linux üzerinde; tek tık kurulum akışını Windows üzerinde çalıştırır.

Skill başlangıç komutu:

```powershell
python .\plugins\project-memory\skills\project-memory\scripts\init_project_memory.py <yeni-proje-klasoru>
```

Hafıza kurulduktan sonra proje içindeki salt okunur sağlık kontrolü:

```powershell
python .\tools\memory_check.py
```

## Güvenlik ve veri koruma sınırları

Başlatıcı yalnızca şablondan oluşturduğu Markdown dosyalarını işler; mevcut belgeleri değiştirmez. Projeye taşınan `tools/init_memory.py`, yanında dağıtılan tarafsız şablonu kullanır; kaynak projenin hafıza kayıtlarını yeni projeye aktarmaz.

Oturum kapatma, yazmadan önce ve sonra sağlık kontrolü yapar; yakalanan yazma veya doğrulama hatalarında oturum ve durum dosyalarını geri yükler. Bu koruma elektrik kesintisine karşı çok dosyalı bir işlem garantisi değildir. Kilitler yalnızca yaşlarına bakılarak silinmez. Oturum geçmişi otomatik kısaltılmaz; arşivleme ayrı bakım işlemidir. `--changed` belirtilen dosyaların proje içinde ve okunabilir olduğunu doğrular; gerçek değişikliklerin bağımsız kanıtı değildir. `--no-durable-change` önceki kalıcı kayıt zamanını korur; kapanış makbuzu ve oturum satırı yine kaydedilir.

Sağlık kontrolündeki gizli bilgi taraması sınırlı bir yardımcı kontroldür. Paylaşmadan önce dosyaları ayrıca gözden geçirin. Yerel Git bundle yalnızca Git geçmişini korur; harici yedek değildir. Güncelleme komutu internette sürüm aramaz, elinizdeki paketi kurar.

## Lisans

MIT — ayrıntılar için `LICENSE` dosyasına bakın.
