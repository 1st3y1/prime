import streamlit as st
import array
import os
import math
import io
import csv
from PIL import Image

DB_FILE = "database.bin"
SAVE_INTERVAL = 10_000_000  # save every 10 million primes

# ---------- Helper Functions ----------
def load_gaps():
    if not os.path.exists(DB_FILE):
        st.warning(f"{DB_FILE} not found. Starting fresh with hard-coded primes.")
        return []
    gaps = array.array('I')
    with open(DB_FILE, 'rb') as f:
        gaps.fromfile(f, os.path.getsize(DB_FILE)//4)
    return list(gaps)

def save_gaps(gaps):
    arr = array.array('I', gaps)
    with open(DB_FILE, 'wb') as f:
        arr.tofile(f)

def reconstruct_primes(gaps):
    primes = [2, 3, 5, 7]
    for g in gaps[4:]:
        primes.append(primes[-1] + g*2)
    return primes

def get_nth_prime(n, gaps):
    first_primes = [2, 3, 5, 7]
    if n <= 4:
        return first_primes[n-1]
    primes = reconstruct_primes(gaps)
    if 1 <= n <= len(primes):
        return primes[n-1]
    return None

def generate_image(size, primes):
    total_pixels = size*size
    img = Image.new("L", (size, size), 255)
    pixels = img.load()
    n = 1
    for y in range(size):
        for x in range(size):
            if n in primes:
                pixels[x, y] = 0
            n += 1
            if n > total_pixels:
                break
        if n > total_pixels:
            break
    return img

def calculate_avg_gaps(block_size, gaps):
    averages = []
    first_primes_count = 4
    total_primes = len(gaps) + first_primes_count
    for i in range(0, total_primes, block_size):
        block_gaps = []
        if i < first_primes_count:
            hardcoded_gaps = [1, 1, 1]
            block_gaps.extend(hardcoded_gaps[i:first_primes_count])
        start_idx = max(0, i - first_primes_count)
        end_idx = start_idx + block_size - len(block_gaps)
        block_gaps.extend([g*2 for g in gaps[start_idx:end_idx]])
        if not block_gaps:
            continue
        avg_gap = sum(block_gaps)/len(block_gaps)
        start_prime_index = i + 1
        averages.append((start_prime_index, avg_gap))
    return averages

# ---------- Load Database ----------
gaps = load_gaps()
primes = reconstruct_primes(gaps)

# ---------- Top Banner Placeholder ----------
banner_placeholder = st.empty()
def update_banner(primes):
    banner_placeholder.markdown(
        f"""
        <div style='background-color:#FFD700; padding:30px; border-radius:5px; text-align:center;'>
            <span style='font-size:36px;'>the current database contains around</span><br>
            <span style='font-size:48px; font-weight:bold;'>{len(primes)//1_000_000} million</span><br>
            <span style='font-size:36px;'>primes</span><br>
            <span style='font-size:18px;'>(approx. {primes[-1]:,} numbers checked)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

update_banner(primes)

st.title("Prime Toolkit Web App (Half-Gap Optimized)")
st.write("Tools: Nth prime finder, prime visualization, average gap analysis, live prime finder.")

# ---------- Nth Prime Finder ----------
st.header("Nth Prime Finder")
n_input = st.number_input("Enter n (positive integer):", min_value=1, step=1)
if st.button("Find nth prime"):
    nth = get_nth_prime(n_input, gaps)
    if nth is not None:
        st.success(f"The {n_input}th prime is: {nth}")
    else:
        st.error("n is out of range for the current database.")

# ---------- Prime Visualization ----------
st.header("Prime Visualization")
img_size = st.number_input("Enter image side in pixels (max 2000 recommended):", min_value=1, step=1, value=500)
if st.button("Generate prime image"):
    if img_size > 2000:
        st.warning("Images larger than 2000x2000 may crash the app. Proceed with caution.")
    img = generate_image(img_size, primes)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    st.image(img, caption=f"Prime Visualization {img_size}x{img_size}", use_column_width=True)
    st.download_button("Download PNG", buf, file_name=f"_pr_vzl_{img_size}.png", mime="image/png")

# ---------- Average Gap Analysis ----------
st.header("Average Gap Analysis")
block_size = st.number_input("Enter number of primes per block:", min_value=1, step=1, value=1000)
if st.button("Calculate average gaps and download CSV"):
    averages = calculate_avg_gaps(block_size, gaps)
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow(["Start Prime #", "Average Gap"])
    for row in averages:
        writer.writerow(row)
    csv_buf.seek(0)
    st.download_button("Download CSV", csv_buf, file_name="gap_anlzd.csv", mime="text/csv")
    st.success(f"CSV generated with {len(averages)} blocks.")

# ---------- Live Prime Finder ----------
st.header("Live Prime Finder")

if "finding_primes" not in st.session_state:
    st.session_state.finding_primes = False

col1, col2 = st.columns(2)
start_button = col1.button("Start Finding Primes")
stop_button = col2.button("Stop Prime Finder")

if start_button:
    st.session_state.finding_primes = True
    st.info("Finding primes... Press 'Stop Prime Finder' to interrupt.")

n_start = primes[-1] + 1
primes_since_save = 0
progress_bar = st.progress(0)
total_checked = 0

while st.session_state.finding_primes:
    n = n_start
    if n % 2 == 0:
        n += 1
    is_prime = True
    limit = int(math.isqrt(n))
    for p in primes:
        if p > limit:
            break
        if n % p == 0:
            is_prime = False
            break
    if is_prime:
        gap = n - primes[-1]
        half_gap = gap if primes[-1] == 2 else gap // 2
        gaps.append(half_gap)
        primes.append(n)
        primes_since_save += 1

        if total_checked % 100 == 0:
            update_banner(primes)

        if primes_since_save >= SAVE_INTERVAL:
            save_gaps(gaps)
            st.success(f"Saved {len(primes)} primes to {DB_FILE}")
            primes_since_save = 0

    n_start += 2
    total_checked += 1
    if total_checked % 1000 == 0:
        progress_bar.progress(min(100, total_checked / 100_000))

    if stop_button:
        st.session_state.finding_primes = False

st.success(f"Prime finding stopped. Total primes: {len(primes)}")
save_gaps(gaps)
update_banner(primes)
