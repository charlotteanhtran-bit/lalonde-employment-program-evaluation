import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from analyze import BASELINE, load_data, analyze, analysis_sample

class AnalysisTests(unittest.TestCase):
    def frame(self):
        rng=np.random.default_rng(42)
        df=pd.DataFrame({c:rng.normal(size=40) for c in BASELINE})
        df['treat']=[0]*20+[1]*20
        df['re78']=1000+250*df.treat+rng.normal(size=40)
        return df
    def test_complete_sample_consistency(self):
        df=self.frame(); df.loc[0,'age']=np.nan
        out=analyze(df)
        self.assertEqual(out['n'],len(analysis_sample(df)))
        self.assertEqual(out['missing_rows_removed'],1)
        self.assertAlmostEqual(out['unadjusted_mean_difference'],analysis_sample(df).groupby('treat').re78.mean().diff().iloc[-1])
    def test_missing_group(self):
        df=self.frame(); df['treat']=0
        with self.assertRaises(ValueError): analyze(df)
    def test_invalid_inputs(self):
        for column,value in [('treat',2),('re78',np.inf)]:
            df=self.frame(); df.loc[0,column]=value
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'data.csv'; df.to_csv(path,index=False)
                with self.assertRaises(ValueError): load_data(path)
