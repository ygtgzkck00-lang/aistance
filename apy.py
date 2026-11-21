using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace BaunAsistan
{
    class Program
    {
        // --- BAUN ASİSTAN AYARLARI ---
        const string BOT_ADI = "BAUN Asistan";
        const string BOT_ACIKLAMA = "Balıkesir Üniversitesi öğrencileri için yapay zekâ destekli asistan. (Günlük kullanım hakkı: 3 soru)";
        const int GUNLUK_SORU_LIMITI = 3;
        const string GEMINI_MODEL = "gemini-2.5-flash";

        const string BOT_KARAKTERI = @"
Sen BAUN Asistan'sın. Balıkesir Üniversitesi (BAUN)
öğrencilerine yardımcı olan, Türkçe konuşan,
samimi, açık ve güvenilir bir üniversite asistanısın.

Üniversite, fakülteler, meslek yüksekokulları, bölümler,
akademik takvim, kayıt, dersler, sınavlar, not sistemi,
öğrenci işleri, kampüs, yemekhane, yurtlar ve üniversite
hizmetleri hakkında soruları yanıtla.

ÖNEMLİ DOĞRULUK KURALLARI:
- Kesin olmayan bilgileri uydurma.
- Güncel bilgiler için Google Search aracını kullan.
- Özellikle BAUN'un resmî internet sitesini ve resmî duyurularını öncelikli kaynak olarak değerlendir.
- Başvuru tarihleri, ücretler, kontenjanlar ve yönetmelikler gibi değişebilen bilgileri mümkün olduğunca doğrula.
- Bilgiyi doğrulayamazsan bunu açıkça belirt.
- Tahminlerini kesin bilgi gibi sunma.
- Üniversite dışındaki genel sorulara da yardımcı ol.
- Kısa, anlaşılır ve doğal cevaplar ver.
- Kullanıcıya Türkçe cevap ver.";

        static readonly HttpClient httpClient = new HttpClient();

        static async Task Main(string[] args)
        {
            Console.OutputEncoding = Encoding.UTF8;
            Console.InputEncoding = Encoding.UTF8;

            Console.WriteLine($"🎓 {BOT_ADI}");
            Console.WriteLine(BOT_ACIKLAMA);
            Console.WriteLine(new string('-', 60));

            // API Anahtarını ortam değişkeninden al (veya doğrudan aşağıya yapıştırabilirsin)
            string apiKey = Environment.GetEnvironmentVariable("GEMINI_API_KEY");
            if (string.IsNullOrWhiteSpace(apiKey))
            {
                Console.Write("GEMINI_API_KEY ortam değişkeni bulunamadı. Lütfen API anahtarını gir: ");
                apiKey = Console.ReadLine()?.Trim();
            }

            if (string.IsNullOrWhiteSpace(apiKey))
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("Hata: Geçerli bir API anahtarı girilmedi. Program kapatılıyor.");
                Console.ResetColor();
                return;
            }

            // Günlük soru sayacı ve sohbet geçmişi
            string kullanimTarihi = DateTime.Today.ToString("yyyy-MM-dd");
            int soruSayisi = 0;
            var messages = new List<ChatMessage>();

            while (true)
            {
                string bugun = DateTime.Today.ToString("yyyy-MM-dd");
                if (kullanimTarihi != bugun)
                {
                    kullanimTarihi = bugun;
                    soruSayisi = 0;
                }

                int kalanHak = Math.Max(0, GUNLUK_SORU_LIMITI - soruSayisi);
                Console.ForegroundColor = ConsoleColor.Cyan;
                Console.WriteLine($"\n📊 Bugünkü kalan soru hakkın: {kalanHak} / {GUNLUK_SORU_LIMITI}");
                Console.ResetColor();

                if (kalanHak <= 0)
                {
                    Console.ForegroundColor = ConsoleColor.Yellow;
                    Console.WriteLine("Günlük 3 soru kullanım hakkın doldu. Yarın tekrar deneyebilirsin.");
                    Console.ResetColor();
                    break;
                }

                Console.Write("\nBAUN hakkında merak ettiğini sor (Çıkmak için 'cikis' yaz): ");
                string prompt = Console.ReadLine()?.Trim();

                if (string.IsNullOrEmpty(prompt))
                    continue;

                if (prompt.Equals("cikis", StringComparison.OrdinalIgnoreCase) ||
                    prompt.Equals("çıkış", StringComparison.OrdinalIgnoreCase))
                    break;

                soruSayisi++;
                messages.Add(new ChatMessage { Role = "user", Content = prompt });

                Console.ForegroundColor = ConsoleColor.DarkGray;
                Console.WriteLine("🔍 BAUN Asistan interneti araştırıyor...");
                Console.ResetColor();

                try
                {
                    var (answer, kaynaklar) = await GeminiSorAsync(apiKey, messages);

                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine($"\n🤖 {BOT_ADI}:");
                    Console.ResetColor();
                    Console.WriteLine(answer);

                    if (kaynaklar.Count > 0)
                    {
                        Console.ForegroundColor = ConsoleColor.Yellow;
                        Console.WriteLine("\n🔎 Yararlanılan Kaynaklar:");
                        Console.ResetColor();
                        foreach (var k in kaynaklar)
                        {
                            Console.WriteLine($"- {k.Title}: {k.Url}");
                        }
                    }

                    // Sadece saf metin yanıtını geçmişe kaydet (kaynak linkleri hariç)
                    messages.Add(new ChatMessage { Role = "model", Content = answer });
                }
                catch (Exception ex)
                {
                    soruSayisi = Math.Max(0, soruSayisi - 1);
                    if (messages.Count > 0 && messages[^1].Role == "user")
                    {
                        messages.RemoveAt(messages.Count - 1);
                    }

                    Console.ForegroundColor = ConsoleColor.Red;
                    Console.WriteLine($"\nGemini API isteği başarısız oldu.\nTeknik hata: {ex.Message}");
                    Console.ResetColor();
                }
            }
        }

        static async Task<(string Answer, List<WebSource> Sources)> GeminiSorAsync(string apiKey, List<ChatMessage> history)
        {
            string url = $"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={apiKey}";

            // API isteği gövdesi (System Instruction + Geçmiş + Google Search Grounding)
            var requestBody = new
            {
                system_instruction = new
                {
                    parts = new[] { new { text = BOT_KARAKTERI } }
                },
                contents = history.Select(m => new
                {
                    role = m.Role,
                    parts = new[] { new { text = m.Content } }
                }).ToArray(),
                tools = new[]
                {
                    new { google_search = new { } }
                }
            };

            string jsonPayload = JsonSerializer.Serialize(requestBody);
            using var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

            HttpResponseMessage response = await httpClient.PostAsync(url, content);
            string responseJson = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                throw new Exception($"HTTP {(int)response.StatusCode}: {responseJson}");
            }

            using JsonDocument doc = JsonDocument.Parse(responseJson);
            JsonElement root = doc.RootElement;

            string answerText = "Şu an yanıt oluşturamadım. Lütfen tekrar dene.";
            var kaynaklar = new List<WebSource>();

            if (root.TryGetProperty("candidates", out JsonElement candidates) && candidates.GetArrayLength() > 0)
            {
                JsonElement firstCandidate = candidates[0];

                // Model cevabını al
                if (firstCandidate.TryGetProperty("content", out JsonElement contentElem) &&
                    contentElem.TryGetProperty("parts", out JsonElement parts) &&
                    parts.GetArrayLength() > 0)
                {
                    var sb = new StringBuilder();
                    foreach (JsonElement part in parts.EnumerateArray())
                    {
                        if (part.TryGetProperty("text", out JsonElement textElem))
                        {
                            sb.Append(textElem.GetString());
                        }
                    }
                    if (sb.Length > 0)
                        answerText = sb.ToString();
                }

                // Google Search kaynaklarını (groundingMetadata) ayrıştır
                if (firstCandidate.TryGetProperty("groundingMetadata", out JsonElement metadata) &&
                    metadata.TryGetProperty("groundingChunks", out JsonElement chunks))
                {
                    foreach (JsonElement chunk in chunks.EnumerateArray())
                    {
                        if (chunk.TryGetProperty("web", out JsonElement web))
                        {
                            string uri = web.TryGetProperty("uri", out JsonElement u) ? u.GetString() : null;
                            string title = web.TryGetProperty("title", out JsonElement t) ? t.GetString() : "Web kaynağı";

                            if (!string.IsNullOrEmpty(uri) && !kaynaklar.Any(k => k.Url == uri))
                            {
                                kaynaklar.Add(new WebSource { Title = title, Url = uri });
                            }
                        }
                    }
                }
            }

            return (answerText, kaynaklar);
        }
    }

    class ChatMessage
    {
        public string Role { get; set; }
        public string Content { get; set; }
    }

    class WebSource
    {
        public string Title { get; set; }
        public string Url { get; set; }
    }
}
