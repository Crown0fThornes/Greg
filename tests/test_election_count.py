from fractions import Fraction
import itertools
import unittest

from commands.election_count import count_stv, validate_ranking


class CountTests(unittest.TestCase):
    def test_twenty_voters_quota_and_bloc_representation(self):
        result=count_stv([1,2,3],[[1,3,2]]*12+[[2,3,1]]*8)
        self.assertEqual(result['quota'],7)
        self.assertEqual(result['winners'],[1,2])
        self.assertEqual(result['tied'],[])
        self.assertEqual(result['rounds'][0]['transfer'],'5/12')
        self.assertEqual(result['rounds'][1]['totals'],{'2':'8','3':'5'})

    def test_fifteen_voters_popular_candidate_and_next_choice(self):
        result=count_stv([1,2,3],[[1,3,2]]*12+[[2,3,1]]*3)
        self.assertEqual(result['quota'],6)
        self.assertEqual(result['winners'],[1,3])
        self.assertEqual(result['rounds'][0]['transfer'],'1/2')

    def test_tied_second_seat_is_reported_for_senior_vote(self):
        # 8 for A; its surplus splits equally between B and C.
        result=count_stv([1,2,3],[[1,2,3]]*4+[[1,3,2]]*4+[[2,3]]*3+[[3,2]]*3)
        self.assertEqual(result['winners'],[1])
        self.assertEqual(result['tied'],[2,3])
        self.assertEqual(result['unfilled'],1)
        self.assertEqual(result['rounds'][-1]['action'],'tie')

    def test_three_way_tie_for_second_seat(self):
        result=count_stv([1,2,3,4],[[1,2]]*3+[[1,3]]*3+[[1,4]]*3)
        self.assertEqual(result['quota'],4)
        self.assertEqual(result['winners'],[1])
        self.assertEqual(result['tied'],[2,3,4])

    def test_ambiguous_elimination_is_not_broken_randomly(self):
        result=count_stv([1,2,3,4],[[1,2]]*4+[[2,1]]*3+[[3,1]]*2+[[4,2]]*2)
        self.assertEqual(result['winners'],[1,2])
        self.assertEqual(result['rounds'][1]['candidates'],[3,4])
        self.assertEqual(result['rounds'][1]['tiebreak'],'batch_elimination')
        self.assertEqual(result['tied'],[])

    def test_previous_round_totals_take_priority_over_borda(self):
        result=count_stv([1,2,3,4],[[1,2]]*8+[[2,3]]+[[3,4]]*3+[[4,3]]*4)
        elimination=result['rounds'][1]
        self.assertEqual(elimination['candidates'],[2])
        self.assertEqual(elimination['tiebreak'],'previous_round_totals')
        self.assertNotIn('borda',elimination)

    def test_borda_breaks_elimination_tie_using_original_rankings(self):
        result=count_stv([1,2,3,4],[[1,3]]*4+[[2,1]]*3+[[3,1]]*2+[[4,2]]*2)
        elimination=result['rounds'][1]
        self.assertEqual(elimination['borda'],{'3':14,'4':6})
        self.assertEqual(elimination['candidates'],[4])
        self.assertEqual(elimination['tiebreak'],'borda')
        self.assertEqual(result['winners'],[1,2])

    def test_legacy_senior_decision_still_replays_at_its_original_round(self):
        ballots=[[1,2]]*4+[[2,1]]*3+[[3,1]]*2+[[4,2]]*2
        number=2
        result=count_stv([1,2,3,4],ballots,elimination_decisions={number:3})
        self.assertEqual(result['rounds'][number-1]['tiebreak'],'senior_council')
        self.assertEqual(result['rounds'][number-1]['candidates'],[3])
        self.assertEqual(result['winners'],[1,2])
        with self.assertRaises(ValueError):
            count_stv([1,2,3,4],ballots,elimination_decisions={number:2})
        with self.assertRaises(ValueError):
            count_stv([1,2,3,4],ballots,elimination_decisions={99:3})

    def test_batch_elimination_can_leave_vacancies_without_inventing_winners(self):
        ballots=[[1,2,3],[1,5,4],[1,4,2],[1,5,3],[2,1,5],[2,3,5],[2,4,1],
                 [3,5,2],[3,4,1],[4,2,1],[4,3,2],[5,2,1],[5,3,4]]
        result=count_stv([1,2,3,4,5],ballots,seats=3)
        self.assertEqual(result['winners'],[1,2])
        self.assertEqual(result['unfilled'],1)
        self.assertEqual(result['tied'],[])
        self.assertIn('batch elimination',result['unfilled_reason'])

    def test_truncated_ballots_exhaust_and_remaining_candidate_can_win(self):
        result=count_stv([1,2,3,4],[[1,2]]*6+[[3,4]]*3)
        self.assertEqual(result['winners'],[1,3])
        self.assertEqual(result['rounds'][-1]['exhausted'],'2')
        self.assertEqual(result['rounds'][-1]['action'],'elect_remaining')

    def test_no_ballots_does_not_elect_candidates(self):
        result=count_stv([1,2],[])
        self.assertEqual(result['winners'],[])
        self.assertEqual(result['unfilled'],2)

    def test_validation(self):
        for ballot in ([1],[1,1],[1,99],[1,2,3,4]):
            with self.assertRaises(ValueError):
                validate_ranking(ballot,[1,2,3])
        self.assertEqual(validate_ranking([3,1],[1,2,3]),[3,1])

    def test_variable_seats_and_more_than_seven_candidates(self):
        candidates=list(range(1,10))
        ballots=[[1,2,3]]*7+[[2,3,1]]*7+[[3,2,1]]*6
        result=count_stv(candidates,ballots,seats=3)
        self.assertEqual(result['quota'],6)
        self.assertEqual(set(result['winners']),{1,2,3})
        self.assertEqual(result['unfilled'],0)
        self.assertEqual(result['seats'],3)
        with self.assertRaises(ValueError):
            count_stv(candidates,[[1,2]],seats=3)

    def test_single_seat_and_invalid_seat_counts(self):
        result=count_stv([1,2,3],[[1]]*3+[[2]]*2,seats=1)
        self.assertEqual(result['winners'],[1])
        self.assertEqual(result['quota'],3)
        for seats in (0,-1,4):
            with self.assertRaises(ValueError):
                count_stv([1,2,3],[],seats=seats)

    def test_ballot_order_never_changes_result_or_rounds(self):
        ballots=[[1,2,3],[1,3,2],[2,3,1],[3,2,1]]
        expected=count_stv([1,2,3],ballots)
        for permutation in itertools.permutations(ballots):
            self.assertEqual(count_stv([1,2,3],permutation),expected)
