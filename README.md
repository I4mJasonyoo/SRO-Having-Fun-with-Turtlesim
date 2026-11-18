# turtle_patrol — Having Fun with Turtlesim (ROS 1)

Package catkin `turtle_patrol` untuk menggerakkan kura-kura di **turtlesim** secara **otonom** (tanpa keyboard, tanpa teleport) memakai **P-controller closed-loop** berbasis `/turtlesim/pose`. Dibuat dan diuji untuk **ROS Noetic** (Python 3).

## Level yang Diselesaikan

| Level | Status | Launch file |
|-------|--------|-------------|
| **Level 1 – Waypoint Patrol** (wajib) | Selesai | `patrol.launch` |
| **Level 2 – Safe Explorer** | Selesai | `explorer.launch` |
| **Level 3 – Hunter** | Selesai | `dogfight_stationary.launch`, `dogfight_patrol.launch`, `dogfight_explorer.launch` |
| **Bonus – Kreasi Bebas** | Menggambar pola dengan pena biru saat patrol; hunter vs target dengan 3 perilaku target (diam, patrol, explorer) | `patrol.launch`, `dogfight_*.launch` |

---

## 1. Struktur Package

```
turtle_patrol/
├── CMakeLists.txt
├── package.xml
├── msg/
│   ├── MissionStatus.msg
│   ├── WallSensor.msg
│   └── HunterScore.msg
├── srv/
│   └── StartMission.srv
├── scripts/
│   ├── waypoint_manager.py      # Level 1 – pengelola waypoint
│   ├── turtle_controller.py     # Level 1 – P-controller
│   ├── virtual_wall_sensor.py   # Level 2 – sensor virtual
│   ├── safe_explorer.py         # Level 2 – penjelajah
│   └── hunter_controller.py     # Level 3 – pemburu
└── launch/
    ├── patrol.launch
    ├── explorer.launch
    ├── dogfight_stationary.launch
    ├── dogfight_patrol.launch
    └── dogfight_explorer.launch
```

---

## 2. Cara Build

Prasyarat: Ubuntu 20.04 + ROS Noetic (`ros-noetic-desktop-full`, sudah termasuk `turtlesim`).

```bash
# 1. Siapkan workspace (lewati jika sudah punya)
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src

# 2. Letakkan package ini di src/
unzip turtle_patrol.zip        # atau: git clone <link-repo>

# 3. Beri izin eksekusi pada script
chmod +x turtle_patrol/scripts/*.py

# 4. Build
cd ~/catkin_ws
catkin_make

# 5. Source workspace
source devel/setup.bash
```

> Jalankan `source ~/catkin_ws/devel/setup.bash` di setiap terminal baru (atau tambahkan ke `~/.bashrc`).

---

## 3. Cara Menjalankan

Setiap level dijalankan dengan **satu perintah `roslaunch`**. `roscore` dan `turtlesim_node` otomatis dijalankan oleh launch file.

### Level 1 – Waypoint Patrol

```bash
roslaunch turtle_patrol patrol.launch
```

Misi **tidak mulai otomatis**. Di terminal lain, panggil service:

```bash
rosservice call /start_mission "start: true"
```

turtle1 akan mengunjungi seluruh waypoint secara berurutan dengan pena biru, lalu berhenti setelah waypoint terakhir.

Memantau status misi:

```bash
rostopic echo /turtle1/mission/status
```

### Level 2 – Safe Explorer

```bash
roslaunch turtle_patrol explorer.launch
```

turtle1 menjelajah arena terus-menerus dan berbelok sebelum menabrak dinding.

### Level 3 – Hunter

Hunter (`turtle_h`) memburu kura-kura `target`. Ada tiga varian sesuai perilaku target:

```bash
roslaunch turtle_patrol dogfight_stationary.launch   # target diam
roslaunch turtle_patrol dogfight_patrol.launch       # target berpatroli mengikuti waypoint
roslaunch turtle_patrol dogfight_explorer.launch     # target menjelajah & menghindari dinding
```

Semuanya berjalan **sepenuhnya otonom** (tidak perlu memanggil service manual). Memantau skor:

```bash
rostopic echo /hunter/score
```

---

## 4. Mengubah Daftar Waypoint

Seluruh waypoint disimpan di **satu tempat**, yaitu list `WAYPOINTS` di bagian atas `scripts/waypoint_manager.py`:

```python
WAYPOINTS = [
    (4.5, 10.0),
    (6.5, 10.0),
    ...
]
DISTANCE_TOLERANCE = 0.1
```

Cukup ubah list tersebut (koordinat dalam rentang turtlesim 0–11). Jumlah waypoint otomatis dihitung dan dipublikasikan lewat parameter `/<turtle>/mission/total_waypoints`. Parameter kontrol lain (`KP_LINEAR`, `KP_ANGULAR`, kecepatan maksimum, toleransi) berada sebagai konstanta di awal masing-masing script.

---

## 5. Arsitektur dan Penjelasan Node

### 5.1 Level 1 – Patrol

![rqt_graph patrol](rqt%20screenshots/patrol.png)

#### `waypoint_manager` (`waypoint_manager.py`)
Pengelola misi. Menyimpan daftar waypoint dan mengirimkannya satu per satu.
- Menyediakan service **`/start_mission`** (`/<turtle>/start_mission` untuk turtle selain turtle1).
- Setelah dimulai, mem-publish waypoint aktif ke `/<turtle>/mission/target` dan mengaktifkan controller lewat `/<turtle>/mission/active`.
- Subscribe `/<turtle>/mission/status`; jika `distance < 0.1` pada waypoint aktif, lanjut ke waypoint berikutnya.
- Mengatur pena lewat service `/<turtle>/set_pen` (pena mati pada waypoint 1, pena biru tebal 3 untuk selanjutnya).
- Setelah waypoint terakhir tercapai: menonaktifkan controller, mematikan pena, dan misi selesai (turtle berhenti).
- Parameter: `~turtle_name` (default `turtle1`).

#### `turtle_controller` (`turtle_controller.py`)
Kontroler closed-loop berbasis pose.
- Subscribe `/<turtle>/pose`, `/<turtle>/mission/target`, `/<turtle>/mission/active`.
- Menghitung jarak dan error sudut ke target, lalu menerapkan **P-controller**:
  - `angular.z = KP_ANGULAR × error_sudut` (maks 4.0 rad/s)
  - `linear.x = KP_LINEAR × jarak` (maks 2.0 unit/s), hanya jika error sudut ≤ 0.05 rad (berputar dulu, baru maju)
- Berhenti saat jarak < `DISTANCE_TOLERANCE` (0.1 unit).
- Mem-publish kecepatan **hanya** ke `/<turtle>/cmd_vel` dan status ke `/<turtle>/mission/status`.
- Parameter: `~turtle_name` (default `turtle1`).

### 5.2 Level 2 – Safe Explorer

#### `virtual_wall_sensor` (`virtual_wall_sensor.py`)
Sensor virtual berbasis *ray casting* terhadap dinding arena (batas efektif 0.5–10.5).
- Subscribe `/<turtle>/pose`, publish `/wall_sensor` (`WallSensor`) pada 20 Hz.
- Mengukur jarak dinding di tiga arah: depan (θ), kiri (θ+45°), dan kanan (θ−45°).
- Menyetel `near_front_wall` dan `near_wall` jika jarak < `SAFE_DISTANCE` (1.0).

#### `safe_explorer` (`safe_explorer.py`)
Penjelajah reaktif berbasis sensor.
- Subscribe `/wall_sensor`, publish `/<turtle>/cmd_vel`.
- Maju lurus (1.5 unit/s). Jika `front_distance < 1.0`, berputar selama 1 detik ke sisi yang lebih lapang (bandingkan jarak kiri vs kanan), lalu maju lagi.
- Parameter: `~turtle_name`.

### 5.3 Level 3 – Hunter

#### `hunter_controller` (`hunter_controller.py`)
- Pada startup: `/kill turtle1`, lalu `/spawn` kura-kura pemburu **`turtle_h`** di tengah arena.
- Spawn kura-kura `target` pada posisi **acak** via service `/spawn` (minimal 2.5 unit dari hunter).
- Mengejar target dengan P-controller yang sama (subscribe `/turtle_h/pose` dan `/target/pose`, publish `/turtle_h/cmd_vel`).
- Saat jarak < **0.5** → `/kill` target, skor +1, publish ke `/hunter/score`, lalu spawn target baru (berulang tanpa henti).
- Parameter `~target_mode`:

| Mode | Perilaku target | Node tambahan |
|------|-----------------|---------------|
| `stationary` | Target diam | – |
| `patrol` | Target mengikuti waypoint; hunter memicunya via service `/target/start_mission` | `waypoint_manager` + `turtle_controller` (`turtle_name=target`) |
| `explorer` | Target menjelajah & menghindari dinding | `virtual_wall_sensor` + `safe_explorer` (`turtle_name=target`, `/wall_sensor` di-remap ke `/target/wall_sensor`) |

---

## 6. Daftar Topic

| Topic | Tipe | Publisher | Subscriber |
|-------|------|-----------|------------|
| `/<turtle>/cmd_vel` | `geometry_msgs/Twist` | `turtle_controller` / `safe_explorer` / `hunter_controller` | `turtlesim` |
| `/<turtle>/pose` | `turtlesim/Pose` | `turtlesim` | controller, sensor, hunter |
| `/<turtle>/mission/target` | `geometry_msgs/PointStamped` | `waypoint_manager` | `turtle_controller` |
| `/<turtle>/mission/active` | `std_msgs/Bool` | `waypoint_manager` | `turtle_controller` |
| `/<turtle>/mission/status` | `turtle_patrol/MissionStatus` | `turtle_controller` | `waypoint_manager` |
| `/wall_sensor` (`/target/wall_sensor` pada dogfight explorer) | `turtle_patrol/WallSensor` | `virtual_wall_sensor` | `safe_explorer` |
| `/hunter/score` | `turtle_patrol/HunterScore` | `hunter_controller` | – (untuk `rostopic echo`) |

`<turtle>` = `turtle1` (patrol/explorer), `turtle_h` (hunter), atau `target`.

## 7. Daftar Service

| Service | Tipe | Server | Fungsi |
|---------|------|--------|--------|
| `/start_mission` (`/target/start_mission` untuk target) | `turtle_patrol/StartMission` | `waypoint_manager` | Memulai misi patrol |
| `/spawn`, `/kill` | `turtlesim/Spawn`, `turtlesim/Kill` | `turtlesim` | Dipakai hunter untuk spawn/hapus kura-kura |
| `/<turtle>/set_pen` | `turtlesim/SetPen` | `turtlesim` | Dipakai `waypoint_manager` untuk mengatur pena |

## 8. Custom Message & Service

### `msg/MissionStatus.msg` — status misi patrol
```
int32   waypoint_index     # waypoint yang sedang dituju (mulai dari 1)
int32   total_waypoints    # jumlah seluruh waypoint
float32 target_x
float32 target_y
float32 distance           # jarak ke waypoint saat ini
bool    mission_complete
```

### `msg/WallSensor.msg` — sensor virtual jarak dinding
```
float32 front_distance
float32 left_distance
float32 right_distance
bool    near_front_wall
bool    near_wall
```

### `msg/HunterScore.msg` — skor permainan hunter
```
int32   score
int32   targets_caught
string  target_name        # target yang baru ditangkap
float32 capture_distance   # jarak saat penangkapan
```

### `srv/StartMission.srv` — memulai misi
```
bool start
---
bool success
string message
```

---

## 9. Kesesuaian dengan Aturan Tugas

- Gerak hanya melalui `/<turtle>/cmd_vel`; **tidak** memakai `turtle_teleop_key`, `teleport_absolute`, maupun `teleport_relative`.
- Keputusan gerak berbasis `/pose` (closed loop), bukan `sleep`/waktu. *(Catatan: pada `safe_explorer`, durasi putar 1 detik adalah pengecualian; keputusan **kapan berbelok** tetap berdasarkan data sensor.)*
- Lebih dari 2 node buatan sendiri yang saling berkomunikasi lewat topic.
- 3 custom message dan 1 custom service.
- Berada dalam package catkin sendiri, dijalankan dengan satu `roslaunch`.

## 10. Troubleshooting

- **`Cannot locate node of type [...py]`** → jalankan `chmod +x scripts/*.py`, lalu `catkin_make` ulang.
- **`Package 'turtle_patrol' not found`** → lupa `source ~/catkin_ws/devel/setup.bash`.
- **Misi patrol tidak bergerak** → `patrol.launch` menunggu pemanggilan `rosservice call /start_mission "start: true"`.
- **Service pena gagal di dogfight patrol** → peringatan sementara saat `target` belum di-spawn; hilang setelah target muncul.

## Screenshot rqt_graph

Tersedia di folder `rqt screenshots/`: `patrol.png`, `explorer.png`, `dogfight_stationary.png`, `dogfight_patrol.png`, `dogfight_explorer rqt.png`.

## Lisensi

MIT
