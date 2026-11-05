# Project Memory Kit

Codex ve Claude Code için kurulabilen, diğer yapay zekâ araçlarında elle kullanılabilen, proje klasöründe yaşayan taşınabilir Markdown hafızası.

## Özellikler

- Proje başına kendi kendine yeterli Markdown hafızası
- Yalnızca gerekli bağlamı yükleyerek düşük token kullanımı
- Gereksinim, karar, mimari, sorun ve öğrenimlerin ayrı tutulması
- Sağlık kontrolü ve doğrulanmış oturum kapanış makbuzu
- Windows'ta tek tık kurulum, yedekli güncelleme ve kaldırma
- Codex skill, yerel plugin ve sağlayıcıdan bağımsız proje şablonu
- Codex ve Claude Code için Windows/macOS/Linux ortak Python kurucusu

## Arkadaşına gönderme

Bu klasörün tamamını ZIP olarak gönderin veya bir Git deposunda paylaşın. Paket kişisel proje hafızası, parola, API anahtarı ya da makineye özel ayar içermez.

## Git adresini vererek yükleme / güncelleme

Ajanınıza “Bu Git adresinden proje hafızasını yükle; kuruluysa güvenli güncelle”
deyin. Bu akışı bilen skill kuruluysa ajan mevcut sağlayıcıyı seçip yerel yöneticiyi
kullanır. İlk kullanımda gözden geçirilmiş ürün paketi gerekir. Komut karşılığı:

```sh
python git_install.py https://example.com/owner/project-memory-kit.git --provider codex
```

Mevcut proje de açıkça kapsamdaysa ajan `--project <proje>` ekler: önce özel
kopyada dener, sonra yedekli günceller. Aksi halde yalnız skill güncellenir.
macOS/Linux'ta `python3` kullanılır. Python 3.10+ ve Git gerekir.

En yüksek kararlı sürüm etiketi ve doğrulanabilir `release.json` aranır; sürümün
kökeni/hashleri kaydedilir. Bilinmeyen eski kurulum veya özel araç değişiklikleri
ezilmez. Yeni sözleşmeyi içeren sürüm yayımlanana kadar mevcut GitHub sürümlerinde
bu yol kullanılamaz. GitHub yayını ve ikinci Windows kabulü bu özellikten ayrıdır.

[Sürüm sözleşmesi, arşivler, eski kurulum ve kurtarma](plugins/project-memory/skills/project-memory/references/git-install.md).

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

### Claude Code kurulumu (Windows, macOS ve Linux)

Python 3.10+ gerekir. Paket kökünde Windows'ta:

```powershell
python install_skill.py install --provider claude
# Yedekli güncelleme:
python install_skill.py install --provider claude --force
# Skill'i kaldırıp yedeğini koruma:
python install_skill.py uninstall --provider claude
```

Hedef `~/.claude/skills/project-memory/` olur. Yeni Claude Code oturumunda
`/project-memory` çağırın; ardından proje hafızasını başlatıp kontrol etmesini isteyin.
Mevcut PowerShell ve çift tık kurucuları Codex içindir; Claude için yukarıdaki
ortak kurucuyu kullanın. Claude uygulaması veya bulut hesabına skill yüklenmez.

### macOS / Linux kurulumu

Python 3.10+ (`python3`) gerekir. Paket kökünde sağlayıcıyı açıkça seçin:

```sh
sh install.sh --provider claude
# Codex için bunun yerine:
sh install.sh --provider codex
# Örnek yedekli güncelleme ve kaldırma:
sh install.sh --provider claude --force
sh uninstall.sh --provider claude
```

Komutlar herhangi bir çalışma klasöründen tam betik yoluyla da çağrılabilir.
`sudo` kullanmayın. Codex hedefi `~/.codex/skills/project-memory/`, Claude hedefi
`~/.claude/skills/project-memory/` olur. Ortak kurucu işletim sisteminin kullanıcı
ev dizinini kullanır; özel profil için `--user-home <dizin>` verilebilir.
Global `AGENTS.md`/`CLAUDE.md`, mevcut projeler ve kurallar değiştirilmez.
Codex'in otomatik global başlatma seçeneği yalnız mevcut PowerShell kurucusundadır.

Ortak kurucu mevcut hedefi `--force` olmadan değiştirmez. Güncelleme önce
kopyayı hash ile doğrular, eski skill'i sağlayıcı dizinindeki
`project-memory-backups/` altına taşır ve yeni kopyayı etkinleştirir. Etkinleştirme
hatasında eski hedefi geri getirir. Kaldırma da skill'i aynı yedek alanına taşır;
yedekler otomatik silinmez ve skill keşif dizininin dışında kalır.
Geri dönmek için çalışan asistan oturumlarını kapatın, mevcut skill'i kaldırın
ve komutun yazdırdığı önceki yedek klasörünü boş olan
`skills/project-memory/` hedefine taşıyın. Başka kurucu eşzamanlı çalıştırmayın;
kesinti sonrası kalan `.project-memory.install.lock` dosyasını ancak ilgili
işlemin artık çalışmadığını doğrulayıp kurulum/yedekleri inceleyince kaldırın.
Bağlantılı (symlink/junction) hedefler ortak kurucuda desteklenmez.

### Claude Code için elle kurulum ve proje talimatı

Kurucusuz kullanımda `plugins/project-memory/skills/project-memory/` klasörünün
**tamamını** boş `~/.claude/skills/project-memory/` hedefine kopyalayın.
Yalnız bu projede kullanmak için alternatif hedef `<proje>/.claude/skills/project-memory/`
olabilir. Mevcut hedefi önce yedekleyin; dosyaları üzerine birleştirmeyin.

Claude'un `AGENTS.md` dosyasını otomatik okuduğunu varsaymayın. Projede
`CLAUDE.md` yoksa oluşturun; varsa mevcut içeriği koruyarak şu kısa yönlendirmeyi ekleyin:

```markdown
Önce AGENTS.md, memory/INDEX.md ve memory/CURRENT.md oku.
Ardından yalnız görevle ilgili 1–3 kaynağı seç; mevcut kayıtları ve yedekleri koru.
```

Bu dosyaları `CLAUDE.md` içine topluca kopyalamayın. Hafıza henüz yoksa önce
aşağıdaki başlatıcıyı kullanın. Skill çağrısı ve talimatların okunması istemci
sürümüne bağlıdır; kurulum testi Claude modelinin protokolü uyguladığının kanıtı değildir.
Hedefler ve çağrı biçimi: [Claude Code skills](https://code.claude.com/docs/en/skills),
proje talimatları: [Claude Code memory](https://code.claude.com/docs/en/memory).

### Sağlayıcıdan bağımsız elle kullanım

macOS/Linux'ta aşağıdaki `python` komutlarında `python3` kullanın.

Skill zorunlu değildir. Paketten `python plugins/project-memory/skills/project-memory/scripts/init_project_memory.py <yeni-proje>` komutunu çalıştırın. Oluşan projedeki `python tools/init_memory.py <başka-yeni-proje>` komutu, skill kurulmadan da yeni bir proje başlatır. Yapay zekâya önce kök `AGENTS.md`, sonra `memory/INDEX.md` ve `memory/CURRENT.md` dosyalarını okumasını söyleyin.

## Mevcut bir projeyi güvenli güncelleme

Kurulu skill'i güncellemek eski projelerin `tools/` dosyalarını değiştirmez.
Yeni paketteki `scripts/update_project_memory.py` önce salt okunur bir plan
üretir, ardından açık `apply` komutuyla araçları yedekli günceller. Önce proje
kopyasında deneyin. Eski paketi `--baseline` olarak verin; değiştirilmiş araçlar
bulunursa işlem durur. Ek özel araçlar korunur; gerçek hafıza ve proje talimatları
yeniden yazılmaz. Güncelleme sonrası proje belgelerinin yeni protokole uyumu
ayrıca incelenir.

[Adım adım plan, uygulama, kurtarma ve geri dönüş](plugins/project-memory/skills/project-memory/references/upgrading.md).

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

GitHub Actions yapılandırması, her push ve pull request için paket testlerini Windows, Linux ve macOS üzerinde; tek tık kurulum akışını Windows üzerinde çalıştıracak şekilde tanımlıdır. Yapılandırma, başarılı CI çalışması kanıtı değildir. macOS veya gerçek Claude Code oturum kabulü ayrıca doğrulanmalıdır.

Skill başlangıç komutu:

```powershell
python .\plugins\project-memory\skills\project-memory\scripts\init_project_memory.py <yeni-proje-klasoru>
```

Hafıza kurulduktan sonra proje içindeki salt okunur sağlık kontrolü:

```powershell
python .\tools\memory_check.py
```

## Güvenlik ve veri koruma sınırları

Kayıt ve kurtarma ayrıntıları: [Güvenli kayıt](plugins/project-memory/skills/project-memory/references/storage.md).

Yarım kalmış bir kayıt tespit edilirse yeni kapanış engellenir. Önce salt okunur kontrol yapın; ardından açık kurtarma komutunu kullanın:

```powershell
python .\tools\memory_check.py
python .\tools\memory_close.py --recover
```

Kurtarma dosya içeriklerini günlüğün hashleriyle karşılaştırır. Dış değişiklik, bozuk kopya veya doğrulanamayan kilit varsa üzerine yazmaz. Canlı süreç kilidi yaşına göre kaldırılmaz. İşlem günlüğünü veya kilidi gelişigüzel silmeyin.

Başlatıcı yalnızca şablondan oluşturduğu Markdown dosyalarını işler; mevcut belgeleri değiştirmez. Projeye taşınan `tools/init_memory.py`, yanında dağıtılan tarafsız şablonu kullanır; kaynak projenin hafıza kayıtlarını yeni projeye aktarmaz.

Oturum kapatma, yazmadan önce ve sonra sağlık kontrolü yapar; yakalanan yazma veya doğrulama hatalarında oturum ve durum dosyalarını geri yükler. İşlem günlüğü kesilen süreçten sonra açık kurtarmayı destekler; elektrik kesintisine karşı çok dosyalı atomiklik garantisi verilmez. Kilitler yalnızca yaşlarına bakılarak silinmez. Oturum geçmişi otomatik kısaltılmaz; arşivleme ayrı bakım işlemidir. `--changed` belirtilen dosyaların proje içinde ve okunabilir olduğunu doğrular; gerçek değişikliklerin bağımsız kanıtı değildir. `--no-durable-change` önceki kalıcı kayıt zamanını korur; kapanış makbuzu ve oturum satırı yine kaydedilir.

Sağlık kontrolündeki gizli bilgi taraması sınırlı bir yardımcı kontroldür. Paylaşmadan önce dosyaları ayrıca gözden geçirin. Yerel Git bundle yalnızca Git geçmişini korur; harici yedek değildir. Güncelleme komutu internette sürüm aramaz, elinizdeki paketi kurar.

## Lisans

MIT — ayrıntılar için `LICENSE` dosyasına bakın.
