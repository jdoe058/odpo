from django.test import SimpleTestCase

from timetable.imports.errors import (
    ScheduleImportError, compress_ranges, group_errors,
)


class CompressRangesTests(SimpleTestCase):
    def test_empty(self):
        self.assertEqual(compress_ranges([]), "")

    def test_single(self):
        self.assertEqual(compress_ranges([9]), "строки 9")

    def test_consecutive(self):
        self.assertEqual(compress_ranges([9, 10, 11, 12]), "строки 9–12")

    def test_mixed(self):
        self.assertEqual(
            compress_ranges([9, 10, 11, 12, 17]),
            "строки 9–12, 17",
        )

    def test_duplicates(self):
        self.assertEqual(compress_ranges([9, 9, 9]), "строки 9")

    def test_unsorted(self):
        self.assertEqual(compress_ranges([12, 9, 10, 11]), "строки 9–12")


class GroupErrorsTests(SimpleTestCase):
    def test_groups_same_message(self):
        # не последовательные строки — проверяем формат "9, 15"
        result = group_errors([
            "Строка 9: сотрудник 'X' не найден",
            "Строка 15: сотрудник 'X' не найден",
        ])
        self.assertEqual(result, ["сотрудник 'X' не найден — строки 9, 15"])

    def test_groups_consecutive_rows_into_range(self):
        # отдельный тест для последовательных — они должны свернуться
        result = group_errors([
            "Строка 9: сотрудник 'X' не найден",
            "Строка 10: сотрудник 'X' не найден",
        ])
        self.assertEqual(result, ["сотрудник 'X' не найден — строки 9–10"])

    def test_different_messages_stay_separate(self):
        result = group_errors([
            "Строка 9: A",
            "Строка 10: B",
        ])
        self.assertCountEqual(result, ["A — строки 9", "B — строки 10"])

    def test_ungrouped_errors_kept_as_is(self):
        result = group_errors(["Не удалось открыть файл: ..."])
        self.assertEqual(result, ["Не удалось открыть файл: ..."])

    def test_mixed(self):
        result = group_errors([
            "Строка 9: A",
            "Строка 15: A",
            "Общая ошибка",
        ])
        self.assertIn("A — строки 9, 15", result)
        self.assertIn("Общая ошибка", result)


class ScheduleImportErrorTests(SimpleTestCase):
    def test_stores_errors(self):
        err = ScheduleImportError(["a", "b"])
        self.assertEqual(err.errors, ["a", "b"])
        self.assertIn("a", str(err))

