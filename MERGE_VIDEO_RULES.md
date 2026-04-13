# Merge Video Rules

Tai lieu nay ghi lai rule hien tai cua tab `Ghep video` de sau nay co the doc lai va nang cap tiep.

## Nguon du lieu

- Thu muc nguon la thu muc `export` chua cac video da split canh.
- Ten file dang theo mau:

`<view>_<title_goc>_<scene_index>.mp4`

Vi du:

- `1.1M_funny dog reaction_1.mp4`
- `1.1M_funny dog reaction_2.mp4`
- `107K_funny dog reaction_12.mp4`

## Cach hieu ten file

- Phan dau la `view` da format ngan:
  - `7.7K`
  - `107K`
  - `1.1M`
  - `13M`
- Phan giua la `title goc`
- Phan cuoi `_1`, `_2`, `_3`... la `scene_index`

## Rule nhom canh

- Cac canh cung mot video goc duoc nhom theo:

`source_key = <view>_<title_goc>`

- Khi ghep video, moi canh la mot clip rieng.

## Rule chon canh

- Muc tieu moi video output:
  - do dai nam trong khoang `62s` den `80s`
  - khong can co dinh dung `62s`
  - neu them mot canh lam tong video vuot `80s` thi bo qua canh do

- Rule thoi luong canh:
  - khong lay canh nao qua `15s` sau khi tinh speed
  - canh tren `5s` se speed `1.25x`
  - canh tren `10s` se speed `1.35x`

- Canh dau tien:
  - muc tieu la tao hook manh trong `3s` den `5s` dau
  - uu tien canh co thoi luong sau speed tu `3s` den `5.5s`
  - neu khong co thi moi noi rong sang khoang `2.5s` den `7s`
  - van uu tien `view` cao, nhung khong chi chon theo view

- 4 canh dau tien:
  - uu tien hook-first: canh ngan, de xem, view cao
  - canh 2 den 4 uu tien khoang `2.5s` den `7s`
  - khong lay canh qua `10s` trong 4 canh dau neu con ung vien khac
  - co gang lay tu nhieu video goc khac nhau de mo dau da dang

- Tu canh thu 5 tro di:
  - duoc random
  - nhung van uu tien canh co `view` cao chua su dung
  - hien tai random co trong so trong `top 5` ung vien view cao nhat

- Cach tinh uu tien canh dau:
  - view cao van la diem chinh
  - canh co duration dep cho hook se duoc cong diem lon
  - canh qua dai o phan dau bi tru diem/bo qua

## Rule tranh lap

- Mot canh da lay roi thi khong duoc lay lai nua.
- Dieu nay ap dung:
  - trong cung mot video output
  - va giua cac video output duoc tao trong cung mot lan chay

## Rule theo video goc

- Moi video goc chi duoc lay toi da `3 canh` trong mot video output.
- Neu da lay nhieu canh tu cung 1 video goc thi:
  - khong duoc lay canh lien nhau
  - vi du khong lay `_1` voi `_2`, hoac `_2` voi `_3`

- Hien tai rule khoang cach canh la:
  - `abs(scene_index_a - scene_index_b) >= 2`

## Rule ve thu tu uu tien

- Cac group video goc duoc sap xep theo `view` giam dan.
- O phan sau video:
  - tool thu tim ung vien hop le chua dung
  - sap xep theo `view_score` giam dan
  - lay `top 5`
  - random co trong so theo `view_score`

## Rule output

- Moi video output hien tai dat ten:
  - `merged_top_1.mp4`
  - `merged_top_2.mp4`
  - ...

- Video duoc ghep bang `ffmpeg concat`.

## Rule chong trung lap (anti-duplicate)

Muc tieu: lam moi video output khac biet ve pixel data, audio fingerprint de TikTok khong detect trung voi video goc.

- Random crop/zoom:
  - crop 2-5% random moi canh, scale lai kich thuoc goc
  - vi tri crop (x, y) cung random de moi canh khac nhau

- Random trim dau:
  - cat 0.1s den 0.3s o dau moi canh
  - thay doi frame dau tien = thay doi thumbnail hash

- Random speed jitter:
  - thay vi co dinh 1.25x hoac 1.35x, random +- 0.08
  - vi du: 1.25x co the thanh 1.18x hoac 1.32x

- Random hue/brightness shift:
  - hue shift +- 3 do moi canh
  - brightness shift +- 3% moi canh
  - mat nguoi khong thay nhung pixel data khac hoan toan

- Film noise/grain:
  - them noise nhe (strength=3) vao output cuoi
  - pha hash pixel ma khong anh huong chat luong

- Audio pitch shift:
  - shift pitch +- 3% moi canh
  - chong audio fingerprint cua TikTok

- Flip canh khong co text:
  - ~35% canh khong co text duoc lat ngang (hflip)
  - detect text bang OpenCV truoc khi flip

## Gia dinh hien tai

- `view` trong ten file la hop le va co the parse duoc thanh so.
- Ten file co dung pattern `_scene_index` o cuoi.
- Thu muc nguon khong co subfolder, cac file video nam cung cap.

## Cac huong nang cap sau nay

- Bat buoc 4 canh dau sap xep dung theo view giam dan tuyet doi.
- Random thong minh hon o phan sau de output khac nhau nhieu hon.
- Them rule tranh lien tiep ve chu de, khong chi theo source.
- Them rule gioi han so canh qua ngan hoac qua dai.
- Them file summary ghi lai moi output da dung nhung canh nao.
