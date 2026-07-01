---
icon: lucide/mic-vocal
---

# Lyrics

Hify can download lyrics and embed them directly into audio files at download time.

## Enabling lyrics

Lyrics are **enabled by default**. You can toggle them in **Settings → Lyrics → Download lyrics**.

## Provider

The only active provider is **[lrclib](https://lrclib.net)** — a free, open, community-maintained lyrics database. No API key is required.

lrclib is queried with the track title, primary artist, album name and duration. It returns:

- **Plain lyrics** — static text, embedded as standard lyrics tags
- **Synced lyrics** — time-coded LRC format, embedded as a separate tag and also saved as a `.lrc` sidecar file alongside the audio

## Embedding

| Format | Plain lyrics tag | Synced lyrics tag |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` with timestamps |
| FLAC | `LYRICS` (Vorbis comment) | `LYRICS` with LRC content |
| M4A | `©lyr` | `©lyr` with LRC content |
| OGG / OPUS | `LYRICS` (Vorbis comment) | `LYRICS` with LRC content |

## Sidecar .lrc file

When synced lyrics are available, Hify also saves a `.lrc` file next to the audio file with the same base name. This lets media players that support external lyrics files (like Jellyfin or certain portable players) show the time-synced lyrics independently of the embedded tags.

## Fallback behaviour

If lrclib returns no result for a track, the download continues normally — the audio file is saved without lyrics. No error is raised.

## Legacy providers

The settings UI may show `genius`, `musixmatch` and `azlyrics` as options inherited from an earlier version of Hify. These are **no-ops** — selecting them has no effect. Only `lrclib` fetches real lyrics.

Để phân tích sâu phần animation, mình sẽ clone trực tiếp source code về để đọc, vì GitHub không cho crawl trực tiếp trang tree.Đã clone repo về và đọc thẳng source (`src/utils/Lyrics/Animator/Lyrics/LyricsAnimator.ts`, `src/modules/Spring.ts`, `LyricsVirtualizer.ts`...). Đây là một engine animation khá tinh vi, không hề dùng CSS transition đơn giản. Phân tích chi tiết:

## 1. Vòng lặp chính

Mọi thứ bắt nguồn từ một `requestAnimationFrame` loop trong `lyrics.ts`: mỗi khung hình đọc `SpotifyPlayer.GetPosition()` (vị trí phát nhạc thực, tính bằng ms), rồi gọi `TimeSetter(progress)` và `Animate(progress)`. Không có `setInterval` cố định fps — animation đồng bộ trực tiếp theo vị trí audio thật, nên nếu nhạc bị seek/buffer, animation tự nhảy theo ngay khung kế tiếp.

`TimeSetter` chỉ làm một việc: gắn `Status` (`NotSung` / `Active` / `Sung`) cho từng line, word/syllable, letter dựa vào so sánh `currentTime` với `StartTime`/`EndTime` — đây là pha "logic", tách biệt khỏi pha "vẽ" do `Animate` đảm nhiệm.

## 2. Lõi vật lý: spring-damper, không phải easing tĩnh

Thay vì dùng `cubic-bezier` hay keyframe animation cố định thời gian, mỗi thuộc tính animate (scale, dịch Y, glow, opacity...) được điều khiển bởi một class `Spring` riêng — port từ thư viện vật lý lò xo nổi tiếng của Roblox/Fraktality (damped harmonic oscillator, giải closed-form chứ không Euler-integrate). Mỗi `Spring` có:

- `frequency` (Hz) — độ "cứng" của lò xo
- `dampingRatio` — độ tắt dần (< 1: underdamped, dao động nảy; = 1: critical; > 1: overdamped, không nảy)
- một "goal" (giá trị đích) có thể đổi liên tục, lò xo sẽ tự追 theo bằng `Step(deltaTime)`

Mỗi cấp phần tử (word, letter, dot, line) có một bộ spring riêng cho `Scale`, `YOffset`, `Glow`, đôi khi thêm `Opacity`. Ví dụ chữ cái dùng `ScaleFrequency=0.88, ScaleDamping=0.64` còn dot (chấm nhạc cụ/interlude) dùng `ScaleFrequency=5, ScaleDamping=0.7` — nảy nhanh và gọn hơn nhiều, tạo cảm giác "pop" khác với chữ.

## 3. Đường cong target: cubic spline theo % tiến trình

Cái spring chỉ追 theo "goal" — còn goal đó lấy từ đâu? Từ các `cubic-spline` (`Spline.at(t)`) được dựng từ vài điểm mốc (keyframe) theo % thời gian hát của từ/chữ, ví dụ:

- `ScaleRange`: 0→0.95, 0.7→~1.05, 1→1 (phình to ở ~70% rồi co lại đúng lúc kết thúc)
- `YOffsetRange`: nhích lên nhẹ rồi hạ xuống đúng lúc âm thanh dứt
- `GlowRange`: tăng dần đến 0.6 rồi giảm về 0

Mỗi frame, code tính `percentage = (now - start)/(end - start)`, lấy `spline.at(percentage)` ra giá trị target, rồi gọi `spring.SetGoal(target)`. Kết quả: chuyển động vừa bám đúng nhịp hát (do spline được tham số hoá theo % thời lượng từ) vừa mềm mại tự nhiên (do spring làm mượt, không giật cục khi goal thay đổi đột ngột).

## 4. Phân cấp animation: Line → Word/Syllable → Letter → Dot

Hệ thống hỗ trợ 3 loại lyric (`Syllable`, `Line`, `Static`). Với loại `Syllable` (karaoke chi tiết nhất), animation lồng nhiều cấp:

- **Line**: class `Active`/`NotSung`/`Sung`, cộng hiệu ứng blur tầng (xem mục 6)
- **Word**: spring riêng cho scale/offset/glow + gradient sweep (mục 5)
- **Letter** (khi `LetterGroup` bật — hiệu ứng tách từng chữ): mỗi chữ có spring riêng, và đặc biệt có thuật toán "proximity falloff" — chữ đang được hát phóng to/nhấp nhô mạnh nhất, các chữ lân cận trong cùng từ giảm dần theo khoảng cách bằng công thức `falloff = 1 / (1 + distance^2.8)`. Đây chính là hiệu ứng kiểu Apple Music lyrics: con trỏ "nhảy" qua từng chữ với vùng ảnh hưởng mượt quanh nó.
- **Dot**: chấm tròn biểu thị đoạn nhạc không lời (interlude), animate scale/offset/glow/opacity riêng theo `DotAnimations`.

## 5. Hiệu ứng "tô màu chạy chữ" (karaoke fill)

Không dùng `background-clip: text` animate bằng JS thuần cho mọi trường hợp. Có 2 cơ chế song song:

- **Chế độ thường**: ghi trực tiếp biến CSS `--gradient-position` mỗi frame (tính theo %), CSS sẽ dùng nó trong `linear-gradient` để tạo dải sáng chạy qua chữ.
- **Simple Lyrics Mode (SLM)** — chế độ nhẹ hơn cho sidebar/mobile: thay vì JS set property mỗi frame, code gắn một CSS `@keyframes SLM_Animation` (chạy bằng `animation: ... linear forwards` với đúng `totalDuration` của từ) để trình duyệt tự nội suy `--SLM_GradientPosition`, đỡ tải JS. Có cả animation "pre" (`Pre_SLM_GradientAnimation`) chạy trước để chuẩn bị gradient của từ kế tiếp, tránh giật khi chuyển từ.

## 6. Glow & Blur theo khoảng cách

- `text-shadow-blur-radius` / `text-shadow-opacity` được set theo giá trị `Glow` spring hiện tại → tạo hiệu ứng "rực sáng" tăng dần khi hát đến từ đó.
- Các dòng **không** active bị áp `--BlurAmount` tăng dần theo khoảng cách tới dòng active (`blurAmount = min(BlurMultiplier * distance, max)`), tạo độ sâu trường ảnh (giống lyrics video Apple Music). Hàm `applyBlur` còn có tối ưu: bỏ qua phần tử đã bị virtualizer unmount (`!el.isConnected`) để tránh ghi style lãng phí vào element không hiển thị.

## 7. Tối ưu performance — đáng chú ý nhất

Đây là phần thể hiện rõ engine này được viết kỹ để chạy 60fps trong môi trường Spicetify (CEF/Electron không mạnh):

- **Style batching**: `setStyleIfChanged()` lưu cache giá trị cũ trong `WeakMap`, chỉ enqueue ghi style nếu thay đổi vượt một epsilon (ví dụ 0.001 cho scale, 0.5px cho blur) — tránh ghi DOM thừa khi spring đã "ngủ" gần goal. `flushStyleBatch()` ghi tất cả thay đổi đã gom một lần ở cuối `Animate()`.
- **GPU promotion**: `will-change: transform, opacity, text-shadow, scale` + `backface-visibility: hidden` được gán cho phần tử lần đầu animate, đẩy element lên compositor layer riêng, tránh repaint toàn trang.
- **`translate3d`** thay `translateY` thường để buộc GPU compositing.
- **Virtualization**: `LyricsVirtualizer.ts` dùng `@tanstack/virtual-core` — chỉ mount DOM cho các dòng nằm trong/khoảng gần viewport, dòng còn lại chỉ là "ước lượng chiều cao" ảo. `Animate()` luôn check `isConnected` trước khi tính toán, nên dù bài hát có hàng trăm dòng, mỗi frame chỉ xử lý vài chục phần tử thật.
- `AnimatorStore` (object chứa các spring) được tạo lười (lazy) — chỉ khởi tạo khi phần tử lần đầu cần animate, tránh tốn bộ nhớ cho lyric chưa từng hiển thị.

## 8. Tự động cuộn theo dòng active

`ScrollToActiveLine.ts` theo dõi dòng active rồi gọi `ScrollTo` qua virtualizer, có cơ chế retry/verify riêng (vì hàng chưa mount chỉ có chiều cao ước lượng, nên lần scroll đầu có thể lệch, code tự đo lại và scroll bù ở frame sau) — tách biệt hoàn toàn khỏi animation chữ/từ, chạy như một "spring" cuộn trang độc lập.

## Tóm lại — điểm hay của thiết kế

Engine này tách rất rõ 3 lớp: **logic trạng thái** (TimeSetter) → **mục tiêu animation theo thời gian hát** (spline theo %) → **chuyển động vật lý mượt** (spring theo thời gian thực, deltaTime). Nhờ tách lớp goal-spline ra khỏi spring, khi goal nhảy đột ngột (ví dụ user seek bài hát), spring không bị "nổ" giá trị mà vẫn mượt mà追 theo. Đây rõ ràng lấy cảm hứng từ extension Beautiful Lyrics (tác giả tự ghi trong README) nhưng được viết lại bằng TypeScript với rất nhiều lớp tối ưu render riêng cho Spicetify/CEF.

Bạn muốn mình đi sâu hơn vào phần nào — ví dụ cơ chế virtualizer/scroll, cách parse file TTML/LRC thành cấu trúc `Syllable`, hay so sánh với cách Beautiful Lyrics làm?
