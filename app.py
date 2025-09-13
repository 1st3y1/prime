import streamlit as st
import array
import os
from PIL import Image
import io
import csv

DB_FILE = "database.bin"

# ---------- Helper Functions ----------

def load_gaps():
    if not os.path.exists(DB_FILE):
        st.error(f"Database file '{DB_FILE}' not found.")
        return []
    gaps = array.array('I')
    with open(DB_FILE, 'rb') as f:
        gaps.fromfile(f, os.path.getsize(DB_FILE) // 4)
    return list(gaps)

def reconstruct_primes(gaps):
    if not gaps:
        return set()
    primes = [gaps[0]]
    for gap in gaps[1:]:
        primes.append(primes[-1] + gap)
    return set(primes)

def get_nth_prime(n, gaps):
    if n < 1 or n > len(gaps):
        return None
    prime = gaps[0]
    for i in range(1, n):
        prime += gaps[i]
    return prime

def generate_image(size, primes):
    """Generate grayscale prime image; return as PIL Image."""
    total_pixels = size * size
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
    total_primes = len(gaps)
    for i in range(0, total_primes, block_size):
        block_gaps = gaps[i:i+block_size]
        if not block_gaps:
            continue
        avg_gap = sum(block_gaps)/len(block_gaps)
        start_prime_index = i + 1
        averages.append((start_prime_index, avg_gap))
    return averages

# ---------- Streamlit Interface ----------

st.title("Prime Toolkit Web App")
st.write("Tools: Nth prime finder, prime visualization, average gap analysis.")

gaps = load_gaps()
primes = reconstruct_primes(gaps)

# --- Nth Prime Finder ---
st.header("Nth Prime Finder")
n_input = st.number_input("Enter n (positive integer):", min_value=1, step=1)
if st.button("Find nth prime"):
    nth = get_nth_prime(n_input, gaps)
    if nth is not None:
        st.success(f"The {n_input}th prime is: {nth}")
    else:
        st.error("n is out of range for the current database.")

# --- Prime Visualization ---
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

# --- Average Gap Analysis ---
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
