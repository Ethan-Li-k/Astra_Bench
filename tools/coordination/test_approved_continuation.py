"""Synthetic approval/continuation fixtures only, under the existing RSI test root."""
import copy
import unittest
import shared_budget as b
import test_empirical_budget as empirical


class ApprovedContinuation(unittest.TestCase):
    setUp = empirical.EmpiricalBudgetTests.setUp
    write_plan = empirical.EmpiricalBudgetTests.write_plan
    reserve = empirical.EmpiricalBudgetTests.reserve

    def evidence_ref(self,path): return {'path':str(path.relative_to(b.ROOT)),'sha256':b.sha(path)}
    def write(self,name,value):
        path=self.f.root/name; b.atomic_write(path,value); return self.evidence_ref(path)

    def prepare(self, prior=True):
        self.base_plan=copy.deepcopy(self.document)
        refs=[]
        if prior:
            prior_ref=self.write('prior-batch.json',{'authorization':'synthetic old six-call authorization',
                'provider':self.document['provider'],'model':'gpt-6-astra','calibration_request_id':'calibration',
                'max_calls':6,'max_payload_bytes':2000,'max_output_tokens':4096})
            rows=[]
            for i in range(1,7):
                rid=f'prior-call-{i:02d}'
                plan=self.base_plan|{'request_id':rid,'batch':prior_ref}
                ref=self.write(f'prior-{i}-plan.json',plan)
                self.f.book.reserve_empirical(ref)
                self.f.book.begin_empirical(rid,self.payload_hash)
                completion=self.complete(rid)
                rows.append({'request_id':rid,'completion_evidence':completion})
            refs=[{'batch':prior_ref,'completed_requests':rows}]
        reviewed=self.write('reviewed-plan.json',{'synthetic':True,'scope':'one episode, max120 calls'})
        self.batch={'authorization':'synthetic explicit approval','batch_id':'test002',
            'provider':self.document['provider'],'model':'gpt-6-astra','reasoning_effort':'xhigh',
            'calibration_request_id':'calibration','max_calls':120,'max_payload_bytes':2000,
            'max_output_tokens':4096,'prior_completed_batches':refs,'automatic_retries':False,
            'new_observation_data_authorized':True}
        self.approval=self.batch|{'schema':1,'approved':True,'provenance':'coordinator-relayed',
            'direct_transcript_verified':False,'user_quote':'API不用审批，超额会暂停，批准计划',
            'coordinator_task_id':'01a0a4fb-3324-7073-b667-4e0e94c54ff2','reviewed_plan':reviewed,
            'destination':self.batch['provider']+'/v1/responses','single_independent_episode':True}
        self.repin()
        self.new_plan(1)

    def repin(self):
        self.batch['approval']=self.write('approval.json',self.approval)
        self.batch_ref=self.write('approved-batch.json',self.batch)

    def new_plan(self,i):
        self.document=self.base_plan|{'request_id':f'test002-call-{i:02d}',
            'call_index':i,'batch':self.batch_ref}
        self.plan=self.f.root/f'new-{i}-plan.json'; self.write_plan()

    def complete(self,rid):
        ref=self.write(f'{rid}-completion.json',{'state':'completed','http_status':200,
            'ledger_request_id':rid,'returned_model':'gpt-6-astra','reasoning_effort':'xhigh',
            'response_id':'SYNTHETIC-response-'+rid,'actual_cny_fen':None,
            'started_at':1,'finished_at':2})
        with self.f.book.transaction() as (state,_): state['requests'][rid]['completion_evidence']=ref
        return ref

    def test_all_120_exact_sequential_count_holds_and_idempotence(self):
        self.prepare()
        for i in range(1,121):
            self.new_plan(i)
            row=self.reserve()
            self.assertEqual(row['reserved_fen'],678)
            self.assertFalse(self.reserve()['created'])
            rid=self.document['request_id']
            self.assertTrue(self.f.book.begin_empirical(rid,self.payload_hash)['transitioned'])
            self.complete(rid)
            self.assertFalse(self.f.book.begin_empirical(rid,self.payload_hash)['transitioned'])
        self.new_plan(121)
        with self.assertRaisesRegex(b.BudgetError,'limit'): self.reserve()
        state=b.load(self.f.ledger)
        self.assertEqual(b.totals(state),(339,126*678))
        self.assertTrue(all('actual_fen' not in row for rid,row in state['requests'].items() if rid!='calibration'))

    def test_missing_or_false_approval_and_above_approved_count(self):
        self.prepare(False)
        for change in ('missing','false','larger','wrong-destination','wrong-provenance'):
            batch=copy.deepcopy(self.batch); approval=copy.deepcopy(self.approval)
            if change=='missing': batch.pop('approval')
            if change=='false': approval['approved']=False
            if change=='larger': batch['max_calls']=121
            if change=='wrong-destination': approval['destination']='https://other.invalid/v1/responses'
            if change=='wrong-provenance': approval['direct_transcript_verified']=True
            if change!='missing': batch['approval']=self.write('invalid-approval.json',approval)
            self.document['batch']=self.write('invalid-batch.json',batch); self.write_plan()
            with self.assertRaises(b.BudgetError,msg=change): self.reserve()

    def test_changed_approval_before_reserve_and_before_begin(self):
        self.prepare()
        self.reserve()
        self.approval['approved']=False
        self.write('approval.json',self.approval)
        with self.assertRaisesRegex(b.BudgetError,'evidence'): self.reserve()
        with self.assertRaisesRegex(b.BudgetError,'evidence'):
            self.f.book.begin_empirical(self.document['request_id'],self.payload_hash)

    def test_changed_reviewed_plan(self):
        self.prepare()
        self.write('reviewed-plan.json',{'changed':True})
        with self.assertRaisesRegex(b.BudgetError,'evidence'): self.reserve()

    def test_foreign_pending_request_never_silently_allowed(self):
        self.prepare()
        with self.f.book.transaction() as (state,_):
            state['requests']['foreign']={'request_id':'foreign','state':'inflight','reserved_fen':100}
        with self.assertRaisesRegex(b.BudgetError,'unsettled'): self.reserve()

    def test_unfinished_prior_and_current_requests_block(self):
        self.prepare()
        with self.f.book.transaction() as (state,_):
            old=state['requests']['prior-call-06'].pop('completion_evidence')
        with self.assertRaisesRegex(b.BudgetError,'unfinished'): self.reserve()
        with self.f.book.transaction() as (state,_): state['requests']['prior-call-06']['completion_evidence']=old
        self.reserve(); self.f.book.begin_empirical(self.document['request_id'],self.payload_hash)
        self.new_plan(2)
        with self.assertRaisesRegex(b.BudgetError,'unfinished'): self.reserve()

    def test_changed_or_incomplete_completion_evidence(self):
        self.prepare()
        ref=self.batch['prior_completed_batches'][0]['completed_requests'][0]['completion_evidence']
        p=b.ROOT/ref['path']; row=b.load(p); row['state']='incomplete'; b.atomic_write(p,row)
        with self.assertRaisesRegex(b.BudgetError,'evidence'): self.reserve()
        new_ref=self.evidence_ref(p)
        with self.f.book.transaction() as (state,_): state['requests']['prior-call-01']['completion_evidence']=new_ref
        self.batch['prior_completed_batches'][0]['completed_requests'][0]['completion_evidence']=new_ref
        self.approval['prior_completed_batches']=copy.deepcopy(self.batch['prior_completed_batches'])
        self.repin(); self.new_plan(1)
        with self.assertRaisesRegex(b.BudgetError,'invalid completed'): self.reserve()

    def test_prior_exact_count_and_no_missing_or_duplicate_ids(self):
        self.prepare()
        for mode in ('missing','duplicate'):
            original=copy.deepcopy(self.batch['prior_completed_batches'])
            refs=self.batch['prior_completed_batches'][0]['completed_requests']
            if mode=='missing': refs.pop()
            else: refs[-1]=refs[0]
            self.approval['prior_completed_batches']=copy.deepcopy(self.batch['prior_completed_batches'])
            self.repin(); self.new_plan(1)
            with self.assertRaisesRegex(b.BudgetError,'count mismatch'): self.reserve()
            self.batch['prior_completed_batches']=original

    def test_global_cap_includes_old_holds_and_no_skipped_indices(self):
        self.prepare()
        self.new_plan(2)
        with self.assertRaisesRegex(b.BudgetError,'consecutive'): self.reserve()
        self.new_plan(1)
        with self.f.book.transaction() as (state,_):
            # Existing synthetic completed holds consume all available global capacity.
            state['requests']['prior-call-01']['reserved_fen']=1_000_000-339-5*678
        with self.assertRaisesRegex(b.BudgetError,'cap exceeded'): self.reserve()
        self.assertEqual(sum(b.totals(b.load(self.f.ledger))),1_000_000)


if __name__ == '__main__': unittest.main()
