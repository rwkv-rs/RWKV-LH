// Exact exhaustive UTF-8 byte n-gram cosine scanner for large frozen datasets.
//
// Input TSV fields: kind (C/H), id, semantic family ("-" for holdout), hex text.
// The implementation accumulates exact 5-byte-gram dot products through an
// inverted index, avoiding an O(records^2 * grams) Python loop.

#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace {

struct Record {
    std::string id;
    std::string family;
    std::string text;
    double norm_squared = 0.0;
};

struct Postings {
    std::vector<std::pair<std::uint32_t, std::uint32_t>> candidates;
    std::vector<std::pair<std::uint32_t, std::uint32_t>> holdouts;
};

std::string decode_hex(const std::string& value) {
    if (value.size() % 2 != 0) {
        throw std::runtime_error("hex text has odd length");
    }
    auto nibble = [](char item) -> unsigned char {
        if (item >= '0' && item <= '9') return static_cast<unsigned char>(item - '0');
        if (item >= 'a' && item <= 'f') return static_cast<unsigned char>(item - 'a' + 10);
        if (item >= 'A' && item <= 'F') return static_cast<unsigned char>(item - 'A' + 10);
        throw std::runtime_error("hex text contains a non-hex character");
    };
    std::string result;
    result.resize(value.size() / 2);
    for (std::size_t index = 0; index < value.size(); index += 2) {
        result[index / 2] = static_cast<char>(
            (nibble(value[index]) << 4) | nibble(value[index + 1])
        );
    }
    return result;
}

std::uint64_t gram_key(const std::string& text, std::size_t offset) {
    std::uint64_t result = 0;
    for (std::size_t index = 0; index < 5; ++index) {
        result = (result << 8) |
            static_cast<unsigned char>(text[offset + index]);
    }
    return result;
}

std::vector<std::string> split_tsv(const std::string& line) {
    std::vector<std::string> fields;
    std::size_t start = 0;
    while (true) {
        const auto position = line.find('\t', start);
        if (position == std::string::npos) {
            fields.push_back(line.substr(start));
            return fields;
        }
        fields.push_back(line.substr(start, position - start));
        start = position + 1;
    }
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: scan_utf8_byte_ngram_cosine INPUT.tsv\n";
        return 2;
    }
    std::ifstream input(argv[1]);
    if (!input) {
        std::cerr << "cannot open input\n";
        return 2;
    }

    std::vector<Record> candidates;
    std::vector<Record> holdouts;
    std::unordered_map<std::uint64_t, Postings> index;
    std::unordered_map<std::string, std::uint32_t> candidate_text_counts;
    std::unordered_set<std::string> holdout_texts;
    std::uint64_t exact_candidate_duplicates = 0;

    std::string line;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        const auto fields = split_tsv(line);
        if (fields.size() != 4 || (fields[0] != "C" && fields[0] != "H")) {
            throw std::runtime_error("invalid input row");
        }
        Record record{fields[1], fields[2], decode_hex(fields[3]), 0.0};
        std::unordered_map<std::uint64_t, std::uint32_t> counts;
        if (record.text.size() >= 5) {
            for (std::size_t offset = 0; offset + 5 <= record.text.size(); ++offset) {
                ++counts[gram_key(record.text, offset)];
            }
        }
        for (const auto& item : counts) {
            record.norm_squared += static_cast<double>(item.second) * item.second;
        }
        if (fields[0] == "C") {
            const auto record_index = static_cast<std::uint32_t>(candidates.size());
            const auto prior = candidate_text_counts[record.text]++;
            exact_candidate_duplicates += prior;
            candidates.push_back(record);
            for (const auto& item : counts) {
                index[item.first].candidates.emplace_back(record_index, item.second);
            }
        } else {
            const auto record_index = static_cast<std::uint32_t>(holdouts.size());
            holdout_texts.insert(record.text);
            holdouts.push_back(record);
            for (const auto& item : counts) {
                index[item.first].holdouts.emplace_back(record_index, item.second);
            }
        }
    }

    const std::size_t candidate_count = candidates.size();
    const std::size_t holdout_count = holdouts.size();
    std::vector<std::uint32_t> candidate_dots(candidate_count * candidate_count, 0);
    std::vector<std::uint32_t> holdout_dots(candidate_count * holdout_count, 0);
    for (const auto& entry : index) {
        const auto& candidate_postings = entry.second.candidates;
        const auto& holdout_postings = entry.second.holdouts;
        for (std::size_t left = 0; left < candidate_postings.size(); ++left) {
            const auto left_index = candidate_postings[left].first;
            const auto left_count = candidate_postings[left].second;
            for (std::size_t right = left + 1; right < candidate_postings.size(); ++right) {
                const auto right_index = candidate_postings[right].first;
                candidate_dots[
                    static_cast<std::size_t>(left_index) * candidate_count + right_index
                ] += left_count * candidate_postings[right].second;
            }
            for (const auto& holdout : holdout_postings) {
                holdout_dots[
                    static_cast<std::size_t>(left_index) * holdout_count + holdout.first
                ] += left_count * holdout.second;
            }
        }
    }

    double maximum_cross_family = 0.0;
    std::string cross_left;
    std::string cross_right;
    for (std::size_t left = 0; left < candidate_count; ++left) {
        for (std::size_t right = left + 1; right < candidate_count; ++right) {
            if (candidates[left].family == candidates[right].family) continue;
            const auto dot = candidate_dots[left * candidate_count + right];
            if (dot == 0) continue;
            const double denominator = std::sqrt(
                candidates[left].norm_squared * candidates[right].norm_squared
            );
            const double score = denominator == 0.0 ? 0.0 : dot / denominator;
            if (score > maximum_cross_family) {
                maximum_cross_family = score;
                cross_left = candidates[left].id;
                cross_right = candidates[right].id;
            }
        }
    }

    double maximum_holdout = 0.0;
    std::string nearest_candidate;
    std::string nearest_holdout;
    std::uint64_t exact_holdout_overlap = 0;
    for (std::size_t candidate = 0; candidate < candidate_count; ++candidate) {
        if (holdout_texts.count(candidates[candidate].text)) ++exact_holdout_overlap;
        for (std::size_t holdout = 0; holdout < holdout_count; ++holdout) {
            const auto dot = holdout_dots[candidate * holdout_count + holdout];
            if (dot == 0) continue;
            const double denominator = std::sqrt(
                candidates[candidate].norm_squared * holdouts[holdout].norm_squared
            );
            const double score = denominator == 0.0 ? 0.0 : dot / denominator;
            if (score > maximum_holdout) {
                maximum_holdout = score;
                nearest_candidate = candidates[candidate].id;
                nearest_holdout = holdouts[holdout].id;
            }
        }
    }

    std::cout << std::setprecision(17);
    std::cout << "candidate_count\t" << candidate_count << "\n";
    std::cout << "holdout_count\t" << holdout_count << "\n";
    std::cout << "exact_candidate_duplicates\t" << exact_candidate_duplicates << "\n";
    std::cout << "exact_holdout_overlap\t" << exact_holdout_overlap << "\n";
    std::cout << "maximum_cross_family\t" << maximum_cross_family << "\t"
              << cross_left << "\t" << cross_right << "\n";
    std::cout << "maximum_holdout\t" << maximum_holdout << "\t"
              << nearest_candidate << "\t" << nearest_holdout << "\n";
    return 0;
}
