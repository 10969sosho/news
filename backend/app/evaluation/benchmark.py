import asyncio
import json
import os
import sys

# Tambahkan root backend ke sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.agent.react_agent import react_agent

async def run_benchmark():
    dataset_path = os.path.join(os.path.dirname(__file__), "sample_claims.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        claims = json.load(f)

    print("=" * 65)
    print("      EVALUASI BENCHMARK SISTEM DETEKSI HOAKS (ReAct + RAG)    ")
    print("=" * 65)
    print(f"Total Klaim Pengujian: {len(claims)}")
    print("-" * 65)

    correct = 0
    total = len(claims)
    y_true = []
    y_pred = []

    for idx, item in enumerate(claims):
        claim_text = item["claim"]
        ground_truth = item["ground_truth"]
        category = item["category"]

        print(f"\n[{idx+1}/{total}] Klaim: {claim_text}")
        print(f"      Kategori: {category}")
        print(f"      Ground Truth: {ground_truth}")

        result = await react_agent.verify(claim_text)
        predicted_status = result.status.value
        confidence = result.confidence

        is_match = (predicted_status == ground_truth)
        if is_match:
            correct += 1
            mark = "✅ TEPAT"
        else:
            mark = "❌ MISMATCH"

        y_true.append(ground_truth)
        y_pred.append(predicted_status)

        print(f"      Prediksi Sistem: {predicted_status} ({mark}) | Keyakinan: {confidence:.2f}")
        print(f"      Iterasi ReAct Digunakan: {result.iterations_used}")
        print(f"      Bukti Terkumpul: {len(result.evidence)} referensi")

    # Hitung Metrik Evaluasi
    accuracy = (correct / total) * 100

    # Binary / Micro precision/recall/f1 untuk kelas Ditolak (Hoaks) vs Lainnya
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == "Ditolak" and yp == "Ditolak")
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != "Ditolak" and yp == "Ditolak")
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == "Ditolak" and yp != "Ditolak")

    precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    print("\n" + "=" * 65)
    print("             RINGKASAN HASIL PENGUJIAN KINERJA SISTEM          ")
    print("=" * 65)
    print(f"1. Akurasi       : {accuracy:.1f}%")
    print(f"2. Presisi Hoaks : {precision:.1f}%")
    print(f"3. Recall Hoaks  : {recall:.1f}%")
    print(f"4. F1-Score      : {f1:.1f}%")
    print("=" * 65)
    print("Perbandingan selesai.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
