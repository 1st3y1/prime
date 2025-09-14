import streamlit as st
import array
import os
import math
import random

DB_FILE = "database.bin"
MIN_BATCH = 100_000
MAX_BATCH = 200_000

# ---------- ADMIN PASSWORD ----------
ADMIN_KEY = st.secrets.get("admin_password", "")

# ---------- Helper Functions ----------
def load_gaps():
    if not os.path.exists(DB_FILE):
        st.warning(f"{DB_FILE} not found. Starting fresh with hard-coded primes.")
        return []
    gaps_arr = array.array('I')
    with open(DB_FILE, 'rb') as f:
        gaps_arr.fromfile(f, os.path.getsize(DB_FILE)//4)
    return list(gaps_arr)

def save_gaps(gaps):
    arr = array.array('I', gaps)
    with open(DB_FILE, 'wb') as f:
        arr.tofile(f)

def reconstruct_primes(gaps):
    """Reconstruct actual prime numbers from half-gaps. First 4 primes are hard-coded."""
    primes = [2, 3, 5, 7]
    last = 7
    for g in gaps[4:]:
        last += g*2
        primes.append(last)
    return primes

def get_nth_prime(n, gaps):
    first_primes = [2, 3, 5, 7]
    if n <= 4:
        return first_primes[n-1]
    primes = reconstruct_primes(gaps)
    if 1 <= n <= len(primes):
        return primes[n-1]
    return None

def total_primes_from_gaps(gaps):
    return 4 + len(gaps[4:])

def format_number(n):
    """Format numbers for banner: millions with two decimals, billions with 3 decimals"""
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.3f}b"
    elif n >= 1_000_000:
        return f"{n/1_000_000:.2f}m"
    else:
        return f"{n:,}"

# ---------- Session State ----------
if "gaps" not in st.session_state:
    st.session_state.gaps = load_gaps()
if "primes_since_save" not in st.session_state:
    st.session_state.primes_since_save = 0
if "n_start" not in st.session_state:
    st.session_state.n_start = 7 if not st.session_state.gaps else reconstruct_primes(st.session_state.gaps)[-1]

# ---------- Top Banner ----------
banner_placeholder = st.empty()
def update_banner():
    total_primes = total_primes_from_gaps(st.session_state.gaps)
    max_checked = reconstruct_primes(st.session_state.gaps)[-1]
    banner_placeholder.markdown(
        f"""
        <div style='background-color:#FFD700; padding:30px; border-radius:5px; text-align:center;'>
            <span style='font-size:36px;'>the current database contains around</span><br>
            <span style='font-size:48px; font-weight:bold;'>{format_number(total_primes)}</span><br>
            <span style='font-size:36px;'>primes</span><br>
            <span style='font-size:18px;'>(approx. {format_number(max_checked)} numbers checked)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

update_banner()

# ---------- App Header ----------
st.title("Prime Finder Web App")

# ---------- Admin-only Database Upload/Download ----------
if ADMIN_KEY:
    key_input = st.text_input("Enter admin key to enable admin tools:", type="password")
    if key_input == ADMIN_KEY:
        st.subheader("Admin Tools")
        uploaded_files = st.file_uploader("Upload your database parts (.bin) or full database", type=["bin"], accept_multiple_files=True)
        if uploaded_files:
            merged_gaps = []
            for file in uploaded_files:
                arr = array.array('I')
                arr.frombytes(file.read())
                merged_gaps.extend(list(arr))
            st.session_state.gaps = merged_gaps
            st.session_state.n_start = reconstruct_primes(st.session_state.gaps)[-1] + 1
            st.session_state.primes_since_save = 0
            update_banner()
            st.success(f"Database uploaded successfully! Total primes: {total_primes_from_gaps(st.session_state.gaps)}")

        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                st.download_button("Download database.bin", f, file_name="database.bin", mime="application/octet-stream")

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
    PRIMES_PER_BATCH = random.randint(MIN_BATCH, MAX_BATCH)
    SAVE_INTERVAL = PRIMES_PER_BATCH

    primes_found = 0
    n = st.session_state.n_start
    if n % 2 == 0:
        n += 1

    # Maintain a working prime list for divisibility check
    first_primes = [2, 3, 5, 7]
    primes_for_check = first_primes[:]
    last_prime = 7
    for g in st.session_state.gaps[4:]:
        last_prime += g*2
        primes_for_check.append(last_prime)

    sub_batch = 10_000
    progress_bar = st.progress(0)

    while primes_found < PRIMES_PER_BATCH:
        limit = int(math.isqrt(n))
        is_prime = True
        for p in primes_for_check:
            if p > limit:
                break
            if n % p == 0:
                is_prime = False
                break

        if is_prime:
            gap = n - last_prime
            half_gap = gap if last_prime == 2 else gap // 2
            st.session_state.gaps.append(half_gap)
            st.session_state.primes_since_save += 1
            primes_found += 1

            last_prime = n
            primes_for_check.append(n)

            if st.session_state.primes_since_save >= SAVE_INTERVAL:
                save_gaps(st.session_state.gaps)
                st.session_state.primes_since_save = 0

        n += 2
        if primes_found % sub_batch == 0:
            progress_bar.progress(primes_found / PRIMES_PER_BATCH)

    st.session_state.n_start = n
    progress_bar.progress(1.0)
    update_banner()
    st.success(f"Processed {primes_found} new primes. Total primes: {total_primes_from_gaps(st.session_state.gaps)}")
