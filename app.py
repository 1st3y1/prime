import streamlit as st
import array
import os
from PIL import Image
import io
import csv

DB_FILE = "database.bin"

# ---------- Highlighted Test Text ----------
st.markdown(
    """
    <div style='background-color:#FFD700; padding:30px; border-radius:5px; text-align:center;'>
        <span style='font-size:36px;'>the current database contains around</span><br>
        <span style='font-size:48px; font-weight:bold;'>70 million</span><br>
        <span style='font-size:36px;'>primes</span><br>
        <span style='font-size:18px;'>(1.397 billion numbers)</span>
    </div>
    """,
    unsafe_allow_html=True
)


st.title("Prime Toolkit Web App (Half-Gap Optimized)")
st.write("Tools: Nth prime finder, prime visualization, average gap analysis.")

# ---------- Helper Functions ----------
def load_gaps():
    if not os.path.exists(DB_FILE):
        st.warning(f"Database file '{DB_FILE}' not found. Using hard-coded first primes.")
        return []
    gaps = array.array('I')
    with open(DB_FILE, 'rb') as f:
        gaps.fromfile(f, os.path.getsize(DB_FILE)//4)
    return list(gaps)

def reconstruct_primes(gaps):
    """Reconstruct primes from half-gaps. First four primes are hard-coded."""
    if not gaps:
        return [2, 3, 5, 7]
    
    primes = [2, 3, 5, 7]
    for g in gaps[4:]:  # skip first four gaps (hard-coded)
        primes.append(primes[-1] + g*2)
    return set(primes)

def get_nth_prime(n, gaps):
    # Handle first four primes manually
    first_primes = [2, 3, 5, 7]
    if n <= 4:
        return first_primes[n-1]

    primes = list(reconstruct_primes(gaps))
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
        # Include first four hard-coded gaps if inside block
        if i < first_primes_count:
            # gaps for 2->3,3->5,5->7
            hardcoded_gaps = [1, 1, 1]  # half-gaps after first prime
            block_gaps.extend(hardcoded_gaps[i:first_primes_count])
            i_offset = max(0, first_primes_count - i)
        else:
            i_offset = 0

        # Add gaps from database
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
