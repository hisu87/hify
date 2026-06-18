# Design System: Apple Music Web Replica

## 1. Core Principles (Nguyên tắc cốt lõi)

- **Content is King:** Hình ảnh (Album Art) là trung tâm. Giao diện xung quanh phải lùi lại để tôn vinh nội dung.
- **Glassmorphism:** Sử dụng hiệu ứng mờ (blur/frosted glass) cho các bề mặt nổi (Sidebar, Player Bar, Modal) để tạo chiều sâu và hòa quyện với màu sắc của Album đang phát.
- **Vibrant & Clean:** Chữ lớn, rõ ràng, độ tương phản cao. Sử dụng màu nhấn (Accent color) một cách tiết chế nhưng nổi bật.

## 2. Design Tokens

### Typography

- **Font Family:** San Francisco (SF Pro Display / SF Pro Text). Nếu không có, fallback sang `Inter`, `Roboto`, hoặc `system-ui`.
- **Weights:** - Regular (400) cho body text.
  - Medium (500) cho sub-titles và metadata.
  - Bold/Semibold (600/700) cho Headings.
- **Tracking (Letter-spacing):** Chữ càng lớn, tracking càng chặt (tight); chữ nhỏ tracking rộng hơn một chút.

### Colors (Tailwind Reference)

- **Background:**
  - Light mode: `#FFFFFF` (Nền chính), `#F2F2F7` (Nền Sidebar).
  - Dark mode: `#000000` (Nền chính), `#1C1C1E` (Nền Sidebar).
- **Accent/Brand:** - Apple Music Pink/Red: `#FA233B` (Sử dụng cho active states, play buttons, links).
- **Text:**
  - Primary: `#1D1D1F` (Light) / `#F5F5F7` (Dark).
  - Secondary (Muted): `#86868B` (Light) / `#A1A1A6` (Dark) - dùng cho tên nghệ sĩ, thời gian.
- **Surfaces (Glass effect):**
  - Player Bar & Header: Nền trong suốt `rgba(255,255,255,0.7)` (Light) hoặc `rgba(0,0,0,0.7)` (Dark) kết hợp `backdrop-filter: blur(20px) saturate(150%)`.

### Spacing & Radii

- **Radii:** - Album Covers: `rounded-md` (6px) hoặc `rounded-lg` (8px).
  - Buttons/Pills: `rounded-full` (hoàn toàn tròn).
  - Cards: `rounded-xl` (12px) cho các banner lớn.
- **Spacing (Grid):** Khoảng cách giữa các item trong grid thường là `gap-4` hoặc `gap-6`. Padding container lớn để tạo không gian thở (thường là `px-8 py-6`).

## 3. Layout Structure

Hệ thống sử dụng bố cục **3 phần (Three-pane layout)**:

1. **Sidebar (Left):** Cố định (Fixed), width khoảng 260px. Chứa điều hướng (Listen Now, Browse, Radio, Library).
2. **Main Content (Center/Right):** Cuộn độc lập (Scrollable). Chứa Hero Banner, Grid danh sách bài hát, Album section.
3. **Player Bar (Bottom):** Cố định dưới cùng (Fixed bottom), width 100%, z-index cao nhất. Chứa control nhạc.

## 4. Key Components Spec

### A. Sidebar Navigation

- **Items:** Icon + Text. Icon sử dụng dạng Outline khi inactive và Solid/Filled khi active. Màu icon đồng bộ với màu text (mặc định) hoặc màu Accent khi được chọn.
- **Hover state:** Background xám nhạt (`hover:bg-gray-200/50` hoặc dark `hover:bg-white/10`), `rounded-md`.

### B. Album Card (Grid Item)

- **Image:** Tỉ lệ 1:1 (Square). Góc bo tròn (`rounded-lg`). Shadow cực nhẹ `shadow-sm`.
- **Hover effect:** Khi hover, xuất hiện nút Play hình tròn (màu nền đục/kính) ở góc dưới cùng bên phải của ảnh. Ảnh có thể scale up nhẹ `scale-105` với `transition-transform duration-300 ease-out`.
- **Text:** - Dòng 1 (Title): Bold, truncate 1 dòng.
  - Dòng 2 (Artist): Regular, màu Secondary, truncate 1 dòng.

### C. Bottom Player Bar

- **Chiều cao:** Cố định khoảng `80px` - `90px`.
- **Background:** Bắt buộc áp dụng Glassmorphism (Backdrop blur). Có đường viền cực mỏng ở cạnh trên (`border-t border-gray-200/20`).
- **Layout (Grid 3 cột):**
  - **Trái (Now Playing):** Ảnh thumbnail nhỏ vuông (bo góc), Tên bài hát (đậm), Tên nghệ sĩ (nhạt).
  - **Giữa (Controls & Progress):** - Nút Play/Pause ở giữa (kích thước lớn nhất). Prev/Next hai bên.
    - Thanh Progress bar mỏng ở dưới. Có chấm tròn nhỏ xuất hiện khi hover.
  - **Phải (Actions):** Volume slider, Queue icon, Lyrics icon.

### D. Hero Banner (Carousel/Header)

- Banner nằm ngang lớn, width 100% container.
- Text overlay ở góc dưới cùng bên trái.
- Sub-text phía trên tiêu đề chính (Ví dụ: "MỚI PHÁT HÀNH" màu secondary).

## 5. Animation & Interactions

- Chuyển động phải mượt mà (fluid), sử dụng cubic-bezier curve (ví dụ: `ease-[cubic-bezier(0.25,0.1,0.25,1)]`).
- Active states trên các nút (nhấn chuột xuống) sẽ scale down nhẹ (`scale-95`).
