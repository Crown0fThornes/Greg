"""Exact STV: Droop quota and weighted inclusive Gregory transfers."""
from fractions import Fraction


def validate_ranking(ranking, candidates, minimum=2):
    if not minimum <= len(ranking) <= len(candidates):
        raise ValueError(f'Rank at least {minimum} candidates, up to all candidates.')
    if len(set(ranking)) != len(ranking) or not set(ranking) <= set(candidates):
        raise ValueError('Rank each candidate at most once, using only this election’s candidates.')
    return list(ranking)


def count_stv(candidates, ballots, seats=2, elimination_decisions=None):
    if not isinstance(seats,int) or seats<1 or len(candidates)<seats or len(set(candidates)) != len(candidates):
        raise ValueError('Choose a positive number of seats and at least that many distinct candidates.')
    ballots = [validate_ranking(ballot, candidates, seats) for ballot in ballots]
    elimination_decisions=dict(elimination_decisions or {})
    used_decisions=set()
    # Fixed positional scores on the original, unweighted ballots. The full
    # nominee count sets the scale; unranked nominees receive zero points.
    borda={candidate:sum(len(candidates)-index-1 for ballot in ballots
                         for index,choice in enumerate(ballot) if choice==candidate) for candidate in candidates}
    quota = len(ballots)//(seats+1)+1
    result = dict(method='Droop quota; weighted inclusive Gregory STV',
                  ballots=len(ballots), seats=seats, quota=quota, winners=[], rounds=[], tied=[], unfilled=seats)
    if not ballots:
        if elimination_decisions:
            raise ValueError('Recorded elimination decisions cannot be applied without ballots.')
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
            current_lowest=[candidate for candidate in candidates if candidate in active and totals[candidate]==min(totals.values())]
            weakest = min(strength(candidate) for candidate in active)
            losers = [candidate for candidate in candidates if candidate in active and strength(candidate)==weakest]
            if len(current_lowest)>1 and len(losers)==1:
                record['tiebreak']='previous_round_totals'
            safe_batch=(totals[losers[0]]==0 and len(active)-len(losers)>=seats-len(result['winners']))
            if len(losers)>1 and not safe_batch:
                record['borda']={str(candidate):borda[candidate] for candidate in losers}
                lowest_borda=min(borda[candidate] for candidate in losers)
                losers=[candidate for candidate in losers if borda[candidate]==lowest_borda]
                if len(losers)==1:
                    record['tiebreak']='borda'
                else:
                    round_number=len(result['rounds'])+1
                    if round_number in elimination_decisions:
                        choice=elimination_decisions[round_number]
                        if choice not in losers:
                            raise ValueError(f'The Senior Council decision for round {round_number} is not one of the tied elimination candidates.')
                        losers=[choice]
                        used_decisions.add(round_number)
                        record['tiebreak']='senior_council'
            if len(losers)>1 and not safe_batch:
                record['tiebreak']='batch_elimination'
            active.difference_update(losers)
            record.update(action='eliminate',candidates=losers)
        result['rounds'].append(record)
        prior_totals.append(totals)
    result['unfilled'] = seats-len(result['winners'])
    if result['unfilled'] and not result['tied']:
        result['unfilled_reason']='Too few nominees remain after batch elimination.'
    if used_decisions!=set(elimination_decisions):
        raise ValueError('A previously recorded Senior Council elimination decision no longer matches the count; counting stopped.')
    return result
