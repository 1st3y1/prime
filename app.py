import streamlit as st
import array
import os
import math
import random

DB_FILE = "database.bin"
PART_SIZE_MB = 24  # Each part ≤ 24 MB
MIN_BATCH = 100_000
MAX_BATCH = 200_000

# ---------- ADMIN PASSWORD ----------
ADMIN_KEY = st.secrets.get("admin_password", "")

# ---------- Helper Functions ----------
def merge_bin_parts():
    """Automatically merge all database.bin.part* files into memory."""
    part_files = sorted([f for f in os.listdir() if f.startswith(DB_FILE + ".part")])
    if not part_files:
        return []
    merged = array.array('I')
    for file in part_files:
        size = os.path.getsize(file)
        if size == 0 or size % 4 != 0:
            st.warning(f"Skipping invalid or empty file {file}")
            continue
        with open(file, 'rb') as f:
            arr = array.array('I')
            arr.fromfile(f, size // 4)
            merged.extend(arr)
    return list(merged)

def load_gaps():
    # Auto-merge parts if they exist
    gaps = merge_bin_parts()
    if gaps:
        return gaps
    # Fallback to single database.bin
    if os.path.exists(DB_FILE):
        arr = array.array('I')
        with open(DB_FILE, 'rb') as f:
            arr.fromfile(f, os.path.getsize(DB_FILE)//4)
        return list(arr)
    return []

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

def format_number(n):
    if n < 1_000_000_000:
        return f"{n / 1_000_000:.2f} m"
    else:
        return f"{n / 1_000_000_000:.3f} b"

# ---------- Session State ----------
if "gaps" not in st.session_state:
    st.session_state.gaps = load_gaps()
if "primes" not in st.session_state:
    st.session_state.primes = reconstruct_primes(st.session_state.gaps)
if "primes_since_save" not in st.session_state:
    st.session_state.primes_since_save = 0
if "n_start" not in st.session_state:
    st.session_state.n_start = st.session_state.primes[-1] + 1

# ---------- Top Banner ----------
banner_placeholder = st.empty()
def update_banner():
    primes = st.session_state.primes
    num_primes_million = len(primes) / 1_000_000
    total_numbers_checked = primes[-1]
    banner_placeholder.markdown(
        f"""
        <div style='background-color:#FFD700; padding:30px; border-radius:5px; text-align:center;'>
            <span style='font-size:36px;'>the current database contains around</span><br>
            <span style='font-size:48px; font-weight:bold;'>{num_primes_million:.2f} million</span><br>
            <span style='font-size:36px;'>primes</span><br>
            <span style='font-size:18px;'>(approx. {format_number(total_numbers_checked)} numbers checked)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

update_banner()
st.title("Prime Finder Web App")

# ---------- Admin-only Database Upload ----------
if ADMIN_KEY:
    key_input = st.text_input("Enter admin key to enable admin tools:", type="password")
    if key_input == ADMIN_KEY:
        st.subheader("Admin Tools")
        uploaded_files = st.file_uploader(
            "Upload database chunks (.bin.part*)", type=["bin", "part"], accept_multiple_files=True
        )
        if uploaded_files:
            merged_gaps = array.array('I')
            for file in uploaded_files:
                content = file.read()
                if len(content) == 0 or len(content) % 4 != 0:
                    st.warning(f"Skipping invalid file {file.name}")
                    continue
                chunk_gaps = array.array('I')
                chunk_gaps.frombytes(content)
                merged_gaps.extend(chunk_gaps)
            st.session_state.gaps = list(merged_gaps)
            st.session_state.primes = reconstruct_primes(st.session_state.gaps)
            st.session_state.n_start = st.session_state.primes[-1] + 1
            st.session_state.primes_since_save = 0
            update_banner()
            st.success(f"Merged {len(uploaded_files)} uploaded chunks.")

# ---------- Nth Prime Finder ----------
st.header("Nth Prime Finder")
n_input = st.number_input("Enter n (positive integer):", min_value=1, step=1)
if st.button("Find nth prime"):
    nth = get_nth_prime(n_input, st.session_state.gaps)
    if nth is not None:
        st.success(f"The {n_input}th prime is: {nth}")
    else:
        st.error("n is out of range for the current database.")

# ---------- Prime Finder ----------
st.header("Prime Finder")
st.markdown(
    "<p style='font-size:18px;'>Clicking this button a few times will help improve the website and make the database bigger</p>",
    unsafe_allow_html=True
)

if st.button("Find next batch of primes"):
    PRIMES_PER_BATCH = random.randint(100_000, 200_000)
    SAVE_INTERVAL = PRIMES_PER_BATCH

    primes_found = 0
    n = st.session_state.n_start
    if n % 2 == 0:
        n += 1

    progress_bar = st.progress(0)
    sub_batch = 10_000

    while primes_found < PRIMES_PER_BATCH:
        is_prime = True
        limit = int(math.isqrt(n))
        for p in st.session_state.primes:
            if p > limit:
                break
            if n % p == 0:
                is_prime = False
                break

        if is_prime:
            gap = n - st.session_state.primes[-1]
            half_gap = gap if st.session_state.primes[-1] == 2 else gap // 2
            st.session_state.gaps.append(half_gap)
            st.session_state.primes.append(n)
            st.session_state.primes_since_save += 1
            primes_found += 1

            if st.session_state.primes_since_save >= SAVE_INTERVAL:
                arr = array.array('I', st.session_state.gaps)
                with open(DB_FILE, 'wb') as f:
                    arr.tofile(f)
                st.session_state.primes_since_save = 0

            if primes_found % sub_batch == 0:
                progress_bar.progress(primes_found / PRIMES_PER_BATCH)

        n += 2

    st.session_state.n_start = n
    progress_bar.progress(1.0)
    update_banner()
    st.success(f"Processed {primes_found} new primes. Total primes: {len(st.session_state.primes)}")
