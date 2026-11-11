"""Exact STV: Droop quota and weighted inclusive Gregory transfers."""
from fractions import Fraction


def validate_ranking(ranking, candidates, minimum=2):
    if not minimum <= len(ranking) <= len(candidates):
        raise ValueError(f'Rank at least {minimum} candidates, up to all candidates.')
    if len(set(ranking)) != len(ranking) or not set(ranking) <= set(candidates):
        raise ValueError('Rank each candidate at most once, using only this election’s candidates.')
    return list(ranking)


def count_stv(candidates, ballots, seats=2):
    if not isinstance(seats,int) or seats<1 or len(candidates)<seats or len(set(candidates)) != len(candidates):
        raise ValueError('Choose a positive number of seats and at least that many distinct candidates.')
    ballots = [validate_ranking(ballot, candidates, seats) for ballot in ballots]
    quota = len(ballots)//(seats+1)+1
    result = dict(method='Droop quota; weighted inclusive Gregory STV',
                  ballots=len(ballots), seats=seats, quota=quota, winners=[], rounds=[], tied=[], unfilled=seats)
    if not ballots:
        return result
    active = set(candidates)
    weights = [Fraction(1) for _ in ballots]
    prior_totals = []
    while active and len(result['winners']) < seats:
        allocations = [next((candidate for candidate in ballot if candidate in active),None)
                       for ballot in ballots]
        totals = {candidate:sum((weights[i] for i,choice in enumerate(allocations)
                                 if choice == candidate),Fraction()) for candidate in active}
        # Earlier totals can resolve an elimination tie, but final-seat ties
        # are always reported for a Senior Member vote.
        def strength(candidate):
            return (totals[candidate],*(round_.get(candidate,Fraction()) for round_ in reversed(prior_totals)))
        record = dict(totals={str(candidate):str(totals[candidate]) for candidate in candidates if candidate in active},
                      exhausted=str(sum((weights[i] for i,choice in enumerate(allocations) if choice is None),Fraction())))
        if len(active) <= seats-len(result['winners']):
            elected = sorted(active,key=strength,reverse=True)
            result['winners'].extend(elected)
            record.update(action='elect_remaining',candidates=elected)
            result['rounds'].append(record)
            break
        if len(set(totals.values())) == 1:
            result['tied'] = [candidate for candidate in candidates if candidate in active]
            record.update(action='tie',candidates=result['tied'])
            result['rounds'].append(record)
            break
        qualified = [candidate for candidate in active if totals[candidate] >= quota]
        if qualified:
            winner = max(qualified,key=lambda candidate:(strength(candidate),-candidates.index(candidate)))
            result['winners'].append(winner)
            transfer = (totals[winner]-quota)/totals[winner]
            for index,choice in enumerate(allocations):
                if choice == winner:
                    weights[index] *= transfer
            active.remove(winner)
            record.update(action='elect',candidates=[winner],transfer=str(transfer))
        else:
            weakest = min(strength(candidate) for candidate in active)
            losers = [candidate for candidate in candidates if candidate in active and strength(candidate)==weakest]
            if len(losers)>1 and (totals[losers[0]]!=0 or len(active)-len(losers)<seats-len(result['winners'])):
                # Choosing arbitrarily here can change who reaches the final.
                # Report all still-contending candidates rather than inventing
                # a winner or excluding someone via an arbitrary tie-break.
                result['tied'] = [candidate for candidate in candidates if candidate in active]
                record.update(action='elimination_tie',candidates=losers)
                result['rounds'].append(record)
                break
            active.difference_update(losers)
            record.update(action='eliminate',candidates=losers)
        result['rounds'].append(record)
        prior_totals.append(totals)
    result['unfilled'] = seats-len(result['winners'])
    return result
