"""Select a synthetic rule's threshold on validation, then inspect test once."""
TRAIN = [(10, 0), (20, 0), (80, 1), (100, 1)]
VALIDATION = [(15, 0), (35, 0), (55, 1), (65, 0), (90, 1)]
TEST = [(25, 0), (45, 1), (60, 0), (75, 1), (95, 1)]


def confusion(rows, threshold):
    counts = dict(tp=0, fp=0, fn=0, tn=0)
    for amount, label in rows:
        prediction = amount >= threshold
        counts[('tp' if label else 'fp') if prediction else ('fn' if label else 'tn')] += 1
    return counts


def cost(rows, threshold):
    counts = confusion(rows, threshold)
    return 4 * counts['fn'] + counts['fp']


if __name__ == '__main__':
    # This baseline is an explicit rule, not a fitted neural model.
    candidates = [30, 50, 70, 90]
    chosen = min(candidates, key=lambda threshold: cost(VALIDATION, threshold))
    print('Validation-selected threshold:', chosen)
    print('Test confusion counts:', confusion(TEST, chosen))
    print('Assumed cost: missed fraud=4, false alarm=1. Change assumptions explicitly.')
