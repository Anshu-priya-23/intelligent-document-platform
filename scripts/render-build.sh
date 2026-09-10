#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

ocr_root="$PWD/.local/ocr"
mkdir -p "$ocr_root/packages"

apt-get update -y

cd "$ocr_root/packages"
apt-get download \
  tesseract-ocr \
  tesseract-ocr-eng \
  tesseract-ocr-osd \
  libtesseract5 \
  liblept5 \
  libgomp1 \
  libwebp7 \
  libgif7 \
  libopenjp2-7 \
  libtiff6 \
  libjpeg62-turbo \
  libpng16-16 \
  libjbig0 \
  libzstd1 \
  liblzma5 \
  libdeflate0 \
  liblerc4 \
  libwebpmux3

for package in ./*.deb; do
  dpkg-deb -x "$package" "$ocr_root"
done

export LD_LIBRARY_PATH="$ocr_root/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export TESSDATA_PREFIX="$ocr_root/usr/share/tesseract-ocr/5/tessdata"

"$ocr_root/usr/bin/tesseract" --version
"$ocr_root/usr/bin/tesseract" --list-langs

if ldd "$ocr_root/usr/bin/tesseract" | grep -q "not found"; then
  echo "Tesseract has unresolved shared libraries." >&2
  exit 1
fi

test -r "$TESSDATA_PREFIX/eng.traineddata"
test -r "$TESSDATA_PREFIX/osd.traineddata"