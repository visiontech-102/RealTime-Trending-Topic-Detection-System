import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

with open("metrics/coherence_diversity.json", encoding="utf-8") as f:
    rows = json.load(f)

models   = ["LDA", "NMF", "BERTopic"]
model_keys = ["lda", "nmf", "bertopic"]
langs    = ["en", "so"]
lang_labels = {"en": "English", "so": "Somali"}

data = {}
for r in rows:
    data[(r["model"], r["language"])] = r["c_v"]

x = np.arange(len(models))
width = 0.32

COLOR_EN = "#1E3A8A"   # brand-primary  (deep blue)
COLOR_SO = "#0EA5E9"   # brand-secondary (cyan)

fig, ax = plt.subplots(figsize=(8, 5))

vals_en = [data.get((m, "en"), 0) for m in model_keys]
vals_so = [data.get((m, "so"), 0) for m in model_keys]

bars_en = ax.bar(x - width/2, vals_en, width, color=COLOR_EN, label="English", zorder=3)
bars_so = ax.bar(x + width/2, vals_so, width, color=COLOR_SO, label="Somali",  zorder=3)

for bar in bars_en:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.008,
            f"{bar.get_height():.4f}", ha="center", va="bottom", fontsize=8.5, color=COLOR_EN, fontweight="bold")
for bar in bars_so:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.008,
            f"{bar.get_height():.4f}", ha="center", va="bottom", fontsize=8.5, color="#0369a1", fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(models, fontsize=12, fontweight="bold")
ax.set_ylabel("C_v Coherence Score", fontsize=11)
ax.set_ylim(0, 0.72)
ax.set_title("C_v Coherence Score Comparison\n(LDA vs NMF vs BERTopic — English & Somali)", fontsize=12, fontweight="bold", pad=14)
ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.5, zorder=2)
ax.text(2.55, 0.502, "0.5 threshold", fontsize=7.5, color="gray", alpha=0.8)
ax.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
ax.set_axisbelow(True)
ax.spines[["top","right"]].set_visible(False)

patch_en = mpatches.Patch(color=COLOR_EN, label="English")
patch_so = mpatches.Patch(color=COLOR_SO, label="Somali")
ax.legend(handles=[patch_en, patch_so], fontsize=10, frameon=False, loc="upper left")

plt.tight_layout()
plt.savefig("coherence_comparison.png", dpi=300, bbox_inches="tight")
plt.savefig("coherence_comparison.pdf", bbox_inches="tight")
print("Saved: coherence_comparison.png  /  coherence_comparison.pdf")
plt.show()
