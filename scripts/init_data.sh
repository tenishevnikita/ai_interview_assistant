#!/bin/bash
set -e

echo "🔄 Обновление чанков..."

# Запускаем все скрипты извлечения
python -m src.data_processing.extract_handbook_python || echo "⚠️ Python handbook extraction failed"
python -m src.data_processing.extract_handbook_ml || echo "⚠️ ML handbook extraction failed"
python -m src.data_processing.extract_handbook_cs || echo "⚠️ CS handbook extraction failed"
python -m src.data_processing.extract_handbook_cpp || echo "⚠️ C++ handbook extraction failed"
python -m src.data_processing.extract_handbook_algo || echo "⚠️ Algorithms handbook extraction failed"
python -m src.data_processing.extract_handbook_linux || echo "⚠️ Linux handbook extraction failed"
python -m src.data_processing.extract_handbook_math || echo "⚠️ Math handbook extraction failed"

echo "🔨 Пересборка FAISS индекса..."
python -m src.data_processing.build_index

echo "✅ Инициализация данных завершена!"

