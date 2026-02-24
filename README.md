# **CD Label Generator**

This project automates the process of identifying audio CDs, collecting metadata, and generating high-quality printable labels for CD sleeves.

I wrote it because I purchased around 800 music CDs in bulk. They did not come with case or sleeve. Some CDs didn't even have the artist or album name written on it. Sorting the collection became somewhat of a problem. I couldn't just pop each and every one into my drive and write the label by hand. So instead I thought why not do this using python.

It is designed for high volume **batch workflows**:

> insert CD → metadata detected → track list fetched → stored in csv → CD ejected → next CD

In the 2nd pass you generate all the labels as images from the data in the CSV file.

The output images are intended to be imported into label software (e.g. DYMO LabelWriter 4XL, Brother, etc.).

This is a **Windows-focused** project, tested with external USB optical drives.

---

## **Features**

* Detects audio CDs via disc ID
* Queries **MusicBrainz** for:

  * Artist
  * Album
  * Year
  * Full track list
* Queries **Discogs** for genre (optional)
* Supports **multiple optical drives simultaneously**
* Automatic **retry + exponential backoff** for unreliable MusicBrainz connections
* Appends results to CSV
* Generates **large landscape labels** including:

  * Artist (bold)
  * Album
  * Year + Genre (right-aligned column)
  * Full track list (auto wrapped)
  * **Automatic truncation + ellipsis when tracks overflow**
  * QR code linking to MusicBrainz release
* Generates **movie labels** including:

  * Title with right-aligned year and runtime
  * MPAA-style certification (e.g., G, PG, PG-13, R)
  * TMDb user rating as a percentage
  * Budget when available
  * Synopsis with cast list appended and truncated to fit
* Automatically ejects discs after processing
* No hardcoded credentials

---

## **System Requirements**

* Windows 10/11
* One or more optical CD drives (USB or internal)
* Internet connection
* Conda (Anaconda or Miniconda)

---

## **Project Structure**

```
cd-label-generator/
├── cd_to_csv.py                 # CD detection + metadata ingestion
├── generate_labels_large.py     # Label rendering
├── movie_to_label.py            # Movie label rendering (TMDb)
├── movie_label_image_manager.py # Movie label layout
├── label_config.py              # Shared label layout constants
├── data/
│   ├── cd_labels.csv            # Metadata store
│   └── gif_labels_large/        # Output images
├── requirements.txt
└── README.md
```

---

## **Installation (Conda Users Only)**

This project intentionally uses **pip inside conda**. This is the correct approach on Windows when native bindings are involved.

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/cd-label-generator.git
cd cd-label-generator
```

### 2. Create environment

```bash
conda create -n cdlabel python=3.11
conda activate cdlabel
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## **requirements.txt**

```text
pandas
python-dotenv
musicbrainzngs
python-discid
discogs-client
qrcode
Pillow
pywin32
```

---

## **Secrets & .env Handling (Automatic)**

This project uses a `.env` file for secrets (Discogs token).

You do **not** need to create or edit this file manually.

On first run:

* If `DISCOGS_TOKEN` is not found, the program will:

  * Prompt you in the console
  * Explain where to get the token
  * Automatically write it to `.env` for future runs

No hardcoded tokens. No manual config editing.

---

## **Discogs Token Setup (Automatic)**

This project optionally uses Discogs to retrieve genre information.

On first run, if no token is found, you will see:

```text
Discogs token not found.
You can create one at: https://www.discogs.com/settings/developers
Enter your Discogs user token:
```

### How to get a discogs token:

1. Go to: [https://www.discogs.com/settings/developers](https://www.discogs.com/settings/developers)
2. Click **Generate new token**
3. Copy the token
4. Paste it into the prompt

### How to get a TMDB token:

1. Go to https://www.themoviedb.org/ for a free account to get a API key.
2. Check your profile. It will be listed under API.
3. The TMDb API key is stored as `TMDB_API_KEY` in `.env`. 

The script will automatically create/update:

```
.env
```

with:

```text
DISCOGS_TOKEN=your_token_here
```

You will not be prompted again.

---

## **Optical Drive Detection**

The script automatically detects **all optical drives** on the system.

* No drive letters are hardcoded
* Multiple drives are supported
* Each drive is monitored independently

Example startup:

```text
Detected optical drives: D:, E:
Waiting for CD insertion on all drives...
```

---

## **Workflow – Step by Step**

### 1. Insert a CD

Insert a CD into **any detected drive**.

---

### 2. Run ingestion

```bash
python cd_to_csv.py
```

The script will:
* Detect the CD
* Read disc ID
* Query MusicBrainz
* Retry automatically on network failure
* Skip + eject if not found
* Query Discogs for genre (if available)
* Append metadata to:
  ```
  data/cd_labels.csv
  ```
* Eject the CD
* Wait for the next disc

Repeat until finished.

---

### 3. Generate labels

```bash
python generate_labels_large.py
```

This will:

* Read `data/cd_labels.csv`
* Fetch full track lists from MusicBrainz
* Render **large landscape labels** into:

  ```
  data/gif_labels_large/
  ```

Each label contains:

* Artist
* Album
* Year
* Genre
* Track list (wrapped + auto truncated)
* QR code

Import these images into your label software.

---

## **Label Design Details**

* Landscape orientation
* Designed for ~4–5 inch wide CD sleeve labels
* Header + subheader layout
* Right-aligned Year / Genre column
* Track list automatically:
  * wraps long titles
  * truncates cleanly when space runs out
  * adds ellipsis to indicate overflow
* QR code placed bottom-right
* No margins (printer software handles margins)

Movie label layout details:
* Title left, year right, runtime right below year
* Rating line under title includes certification, TMDb user rating percentage, and budget
* Synopsis is followed by a cast line; both are wrapped and truncated to fit

---

## **Important Behavior Notes**

* **MusicBrainz access is unreliable** → handled with exponential backoff + jitter
* **Track lists are fetched at render time**, not stored in CSV
* **CSV is the authoritative list of CDs**
* **If a CD is not found, it is skipped and ejected (no infinite loops)**
* **Year is normalized (no `1998.0`, no `nan`)**
* **Genre may be blank**
* **QR codes are URLs (not base64 blobs) for scanner compatibility**
* **No manual config files required**
* **Movie ratings come from TMDb certifications (e.g., PG-13), not vote averages**
* **TMDb vote averages are displayed as percentages (vote_average * 10)**

---

## **Why Conda + Pip**

This project intentionally uses:

```text
conda → environment + native libs
pip   → Python ecosystem packages
```

Because on Windows:

* `python-discid`, `musicbrainzngs`, and `qrcode` are not reliably available via conda-forge
* Conda provides stability
* Pip provides completeness

This is standard practice for real Windows projects with native bindings.

---

## **License**

MIT

---

## **Final Note**

This is not a toy script.
It is a full ingestion + rendering pipeline designed for real batch workflows.

Insert discs. Get back labels.

## TODO

test this. Generate labels large and cd_to_label can be further combined.