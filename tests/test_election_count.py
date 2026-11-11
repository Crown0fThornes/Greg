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
        self.assertEqual(result['winners'],[1])
        self.assertEqual(result['rounds'][-1]['action'],'elimination_tie')
        self.assertEqual(result['tied'],[2,3,4])

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

    def test_ballot_order_never_changes_result_or_rounds(self):
        ballots=[[1,2,3],[1,3,2],[2,3,1],[3,2,1]]
        expected=count_stv([1,2,3],ballots)
        for permutation in itertools.permutations(ballots):
            self.assertEqual(count_stv([1,2,3],permutation),expected)
