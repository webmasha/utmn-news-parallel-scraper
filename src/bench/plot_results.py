import json
import matplotlib.pyplot as plt
from pathlib import Path

def plot_results():
    """
    Создает и сохраняет графики на основе последнего файла с результатами бенчмарка.

    Функция выполняет следующие действия:
    1. Находит самый свежий `.json` файл в директории `src/bench/results`.
    2. Загружает данные из этого файла.
    3. Создает два графика:
       - `comparison_chart.png`: Сравнительная диаграмма производительности
         последовательного, асинхронного и лучшего гибридного режимов.
       - `hybrid_scaling_chart.png`: График масштабируемости гибридной модели,
         показывающий зависимость времени выполнения от количества воркеров.
    4. Сохраняет графики в ту же директорию `results`.
    """
    results_dir = Path(__file__).parent / "results"
    if not results_dir.exists():
        print(f"Директория с результатами не найдена: {results_dir}")
        return

    # Находим последний по времени изменения файл с результатами
    try:
        latest_result_file = max(results_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
    except ValueError:
        print(f"Файлы с результатами бенчмарков не найдены в {results_dir}")
        return

    with open(latest_result_file, "r") as f:
        data = json.load(f)
        print(f"Данные загружены из {latest_result_file}")

    labels = list(data.keys())
    times = [d['time'] for d in data.values()]

    # Отделяем гибридные результаты для специального графика
    hybrid_labels = sorted([k for k in labels if k.startswith("hybrid")], key=lambda x: int(x.split('_')[1]))
    hybrid_times = [data[k]['time'] for k in hybrid_labels]
    hybrid_workers = [int(k.split('_')[1]) for k in hybrid_labels]

    # --- Основной график сравнения ---
    plt.figure(figsize=(12, 7))
    non_hybrid_labels = [l for l in labels if not l.startswith("hybrid")]
    non_hybrid_times = [data[l]['time'] for l in non_hybrid_labels]
    
    # Для общего сравнения добавляем лучший результат гибридной модели
    if hybrid_labels:
        best_hybrid_label = hybrid_labels[hybrid_times.index(min(hybrid_times))]
        non_hybrid_labels.append(best_hybrid_label)
        non_hybrid_times.append(min(hybrid_times))

    plt.bar(non_hybrid_labels, non_hybrid_times, color=['skyblue', 'lightgreen', 'coral'])
    plt.ylabel("Время выполнения (секунды)")
    plt.title("Сравнение производительности: последовательный, асинхронный и гибридный режимы")
    plt.xticks(rotation=15)
    plt.tight_layout()
    
    save_path = results_dir / "comparison_chart.png"
    plt.savefig(save_path)
    print(f"График сравнения сохранен: {save_path}")

    # --- График масштабируемости гибридной модели ---
    if hybrid_workers:
        plt.figure(figsize=(10, 6))
        plt.plot(hybrid_workers, hybrid_times, marker='o-', linestyle='--')
        plt.xlabel("Количество процессов-воркеров")
        plt.ylabel("Время выполнения (секунды)")
        plt.title("Масштабируемость гибридной модели")
        plt.xticks(hybrid_workers)
        plt.grid(True)
        plt.tight_layout()
        
        save_path = results_dir / "hybrid_scaling_chart.png"
        plt.savefig(save_path)
        print(f"График масштабируемости сохранен: {save_path}")

if __name__ == "__main__":
    plot_results()
