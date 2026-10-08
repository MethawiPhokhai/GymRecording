# วิเคราะห์: รีดีไซน์หน้า Plan ตาม Claude Design (Design A · One compact list)

> ที่มา: `Plan Mobile v2.html` + README ใน handoff zip (implement เฉพาะ Design A)
> โค้ดปัจจุบัน: `build.py` (`build_template_section`, `SAVE_SCRIPT`, `STYLE`, `build_html`)

## 1. ปัญหาของหน้า Plan เดิม

- ทุก routine เป็นตารางกว้างแยกกัน (Exercise / Weight / Sets×Reps) → เลื่อนยาวและแน่นบนมือถือ
- ช่อง input 3 ช่องต่อแถว ทำให้กดยาก (touch target เล็ก)
- ท่าที่ซ้ำหลาย routine (Squat, Tibialis raise, Back cable rowing ฯลฯ) ติ๊กแยกกันได้ → เสี่ยงบันทึกซ้ำ
- Cardio (Class / Running / Cycling) ปนอยู่ท้ายหน้า strength

## 2. สิ่งที่จะทำ

| ส่วน | ดีไซน์ | วิธีทำใน `build.py` |
|---|---|---|
| Header | "Plan" + `last session … · N workouts` + สวิตช์ lbs/kg | sticky ทั้งก้อน (`.plan-head`) → **สวิตช์หน่วยอยู่ในระยะมือตลอด** ตามกฎโปรเจกต์ |
| Mode | Strength \| Cardio + badge จำนวนที่ติ๊ก | แท็บ `#pt-s` / `#pt-c`; Class/Running/Cycling ย้ายไปแท็บ Cardio |
| Routine chips | เลื่อนแนวนอน กดแล้ว scroll ไป section, chip active ตาม scroll | สร้างจาก template ที่มี `exercises` สีจาก `TYPE_COLORS` |
| Section header | sticky, `n/total`, Tick all / Clear | `.psh` (sticky ใต้ `.plan-head`) |
| Row | checkbox 44px, ชื่อ + muscle + "also in …", value chip | `div.sel-row` แทน `<tr>`; input เดิม (`.w-num`, `.sr-sets`, `.sr-reps`) ยังอยู่แต่ซ่อน |
| Edit sheet | bottom sheet: Weight / Sets / Reps แบบ stepper + quick add + BW | `#psheet` แก้ค่าใน hidden input เดิม |
| Save bar | ลอย, "n selected" + จุดสี routine ที่ติ๊ก + Save | ใช้ `#savebar/#savebtn/#tokenbtn` เดิม เปลี่ยนหน้าตา |

## 3. ข้อตกลงที่คงไว้ / ตัดสินใจ

- **Data model ไม่เปลี่ยน** — ยังเก็บ lbs อย่างเดียว (`weight_lbs`), `data-lbs` ยังเป็นค่า canonical, `rowData()` ยังเขียนไฟล์ในรูปแบบเดิม ไม่ต้องแก้ CI/`resolve_session`
- **หน่วย**: ใช้สวิตช์เดียวทั้งหน้า (`localStorage.wunit`) ตามเดิม; ในหน้า Plan สวิตช์อยู่ใน header ที่ sticky และซ้ำอีกในแผ่นแก้ไข ไม่มี input น้ำหนักสองช่องคู่กัน
- **ติ๊กตามชื่อท่าแบบ global**: ท่าชื่อเดียวกันใน routine อื่น ติ๊ก/แก้ค่าพร้อมกัน และ `selections()` ตัดซ้ำ (log ครั้งเดียว ใต้ routine แรกที่พบ) ชื่อที่มี `* ` นำหน้ายังถือเป็นคนละท่าตาม AGENTS.md
- **Reps แบบรายเซ็ต** (`12 10 10 8`) ยังใช้ได้: stepper ปรับทุกค่าพร้อมกัน
- **"+ Add exercise"** อยู่ท้ายแต่ละ routine (ต้องรู้ type เพื่อตั้งชื่อไฟล์ตอน save)
- Cardio เดิม (Class chips, ฟอร์ม Running/Cycling) คง logic เดิม แค่ย้ายแท็บและปรับสี
- ใช้ design tokens จาก handoff (scope ใน `.plan`) ไม่ไปกระทบหน้า Weight/Cardio
- Desktop: จำกัดความกว้าง ~640px จัดกึ่งกลาง

## 4. ไม่ได้ทำ

- ไม่เปลี่ยนการเก็บหน่วยเป็น kg/คำนวณ km↔mi (README บอกให้ตัดสินใจกับ backend; ที่นี่ Running ยังเป็น km)
- ไม่ implement Design B
