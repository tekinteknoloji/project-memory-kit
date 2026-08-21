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
python .\tests\test_package.py
.\tests\test_one_click.ps1
```

GitHub Actions, her push ve pull request için paket testlerini Windows ve Linux üzerinde; tek tık kurulum akışını Windows üzerinde çalıştırır.

Skill başlangıç komutu:

Skill sağlık kontrolü:

```powershell
python .\plugins\project-memory\skills\project-memory\scripts\init_project_memory.py --help
```

Yeni projedeki hafıza kurulduktan sonra proje içindeki şu komut kullanılabilir:

```powershell
python .\tools\memory_check.py
```

## Lisans

MIT — ayrıntılar için `LICENSE` dosyasına bakın.
