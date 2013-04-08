import unittest
import os
import cPickle as pickle
import skrf as rf
import numpy as npy

class OnePortStandardCalibration(unittest.TestCase):
    '''
    One-port calibration test.

    loads data for a reciprocal embeding network, and some ideal
    standards. ficticous measurements are made by cascading the ideals
    behind teh embeding network, and a calibration is performed.

    the calculated embedding network and de-embeded ideals are compared
    to originals as a metric of 'working'

    '''
    def setUp(self):
        test_dir = os.path.dirname(__file__)
        self.short = rf.Network(os.path.join(test_dir, 'short.s1p'))
        self.match = rf.Network(os.path.join(test_dir, 'match.s1p'))
        self.open = rf.Network(os.path.join(test_dir, 'open.s1p'))
        self.delay_short = rf.Network(os.path.join(test_dir,
                                                   'delay short.s1p'))
        self.embeding_network = rf.Network(os.path.join(test_dir,
                                               'embedingNetwork.s2p'))
        self.test_dir = test_dir

    def test_standard_calibration(self):
        ideals, measured = [], []
        std_list = [self.short, self.match,self.open]

        for ntwk in std_list:
            ideals.append(ntwk)
            measured.append(self.embeding_network ** ntwk)

        cal = rf.Calibration(\
                ideals = ideals,\
                measured = measured,\
                type = 'one port',\
                is_reciprocal = True,\
                )
        # did we find correct embeding network?
        self.assertEqual(self.embeding_network, cal.error_ntwk)
        # are the de-embeded networks the same as their ideals?
        for ntwk in std_list:
            self.assertEqual(ntwk, cal.apply_cal(self.embeding_network**ntwk))
    
    def test_least_squares_calibration(self):
        ideals, measured = [],[]
        std_list = [self.short, self.match,self.open,self.delay_short]

        for ntwk in std_list:
            ideals.append(ntwk)
            measured.append(self.embeding_network**ntwk)

        cal = rf.Calibration(\
                ideals = ideals,\
                measured = measured,\
                type = 'one port',\
                is_reciprocal = True,\
                )
        # did we find correct embeding network?
        self.assertEqual(self.embeding_network, cal.error_ntwk)
        # are the de-embeded networks the same as their ideals?
        for ntwk in std_list:
            self.assertEqual(ntwk,  cal.apply_cal(self.embeding_network**ntwk))
    
    def test_pickling(self):
        ideals, measured = [], []
        std_list = [self.short, self.match,self.open]

        for ntwk in std_list:
            ideals.append(ntwk)
            measured.append(self.embeding_network ** ntwk)

        cal = rf.Calibration(\
                ideals = ideals,\
                measured = measured,\
                type = 'one port',\
                is_reciprocal = True,\
                )
        
        original = cal
        
        f = open(os.path.join(self.test_dir, 'pickled_cal.cal'),'wb')
        pickle.dump(original,f)
        f.close()
        f = open(os.path.join(self.test_dir, 'pickled_cal.cal'))
        unpickled = pickle.load(f)
        a = unpickled.error_ntwk
        unpickled.run()
        
        
        # TODO: this test should be more extensive 
        self.assertEqual(original.ideals, unpickled.ideals)
        self.assertEqual(original.measured, unpickled.measured)
        
        f.close()
        os.remove(os.path.join(self.test_dir, 'pickled_cal.cal'))


class TwoPortCalibration8term(unittest.TestCase):
    def test_accuracy(self):
        wg= rf.wr10
        wg.frequency = rf.F.from_f([1])
         
        X = wg.match(nports =2, name = 'X')
        Y = wg.match(nports =2, name='Y')
        X.s = rf.rand_c(len(wg.frequency),2,2)
        Y.s = rf.rand_c(len(wg.frequency),2,2)
        
        
        ideals = [
            wg.short(nports=2, name='short'),
            wg.open(nports=2, name='open'),
            wg.match(nports=2, name='load'),
            wg.thru(name='thru'),
            ]
        
        measured = [X**k**Y for k in ideals]
        
        cal = rf.Calibration(
            ideals = ideals,
            measured = measured,
            )
        for k in range(cal.nstandards):
            self.assertTrue(cal.apply_cal(measured[k]) == ideals[k]) 
          
class TwoPortCalibrationSOLT(unittest.TestCase):
    def setUp(self):
        wg= rf.wr10
        wg.frequency = rf.F.from_f([1])
         
        self.Xf = wg.match(nports =2, name = 'Xf')
        self.Xr = wg.match(nports =2, name = 'Xr')
        self.Yf = wg.match(nports =2, name='Yf')
        self.Yr = wg.match(nports =2, name='Yr')
        self.Xf.s = rf.rand_c(len(wg.frequency),2,2)
        self.Xr.s = rf.rand_c(len(wg.frequency),2,2)
        self.Yf.s = rf.rand_c(len(wg.frequency),2,2)
        self.Yr.s = rf.rand_c(len(wg.frequency),2,2)
        
        ideals = [
            wg.short(nports=2, name='short'),
            wg.open(nports=2, name='open'),
            wg.match(nports=2, name='load'),
            wg.thru(name='thru'),
            ]
        
        measuredf = [self.Xf**k**self.Yf for k in ideals]
        measuredr = [self.Xr**k**self.Yr for k in ideals]
        measured = [ k.copy() for k in measuredf]
        
        for m,f,r  in zip(measured,measuredf, measuredr):
            m.s[:,1,0] = f.s[:,1,0]
            m.s[:,0,0] = f.s[:,0,0]
            m.s[:,0,1] = r.s[:,0,1]
            m.s[:,1,1] = r.s[:,1,1]
            
        self.cal = rf.SOLT(
            ideals = ideals,
            measured = measured,
            )
    
    def test_forward_directivity_accuracy(self):
        self.assertEqual(
            self.Xf.s11,
            self.cal.coefs_ntwks['forward directivity'])
    
    def test_forward_source_match_accuracy(self):
        self.assertEqual(
            self.Xf.s22 , 
            self.cal.coefs_ntwks['forward source match'] )       
    
    def test_forward_load_match_accuracy(self):
        self.assertEqual(
            self.Yf.s11 , 
            self.cal.coefs_ntwks['forward load match'])
    
    def test_forward_reflection_tracking_accuracy(self):
        self.assertEqual(
            self.Xf.s21 * self.Xf.s12 , 
            self.cal.coefs_ntwks['forward reflection tracking'])
    
    def test_forward_transmission_tracking_accuracy(self):
        self.assertEqual(
            self.Xf.s21*self.Yf.s21 , 
            self.cal.coefs_ntwks['forward transmission tracking'])
    
    def test_reverse_source_match_accuracy(self):
        self.assertEqual(
            self.Yr.s11 , 
            self.cal.coefs_ntwks['reverse source match']   )     
    
    def test_reverse_directivity_accuracy(self):
        self.assertEqual(
            self.Yr.s22 , 
            self.cal.coefs_ntwks['reverse directivity']  )      
    
    def test_reverse_load_match_accuracy(self):
        self.assertEqual(
            self.Xr.s22 , 
            self.cal.coefs_ntwks['reverse load match'])
    
    def test_reverse_reflection_tracking_accuracy(self):
        self.assertEqual(
            self.Yr.s21 * self.Yr.s12 , 
            self.cal.coefs_ntwks['reverse reflection tracking'])
    
    def test_reverse_transmission_tracking_accuracy(self):
        self.assertEqual(
            self.Yr.s12*self.Xr.s12 , 
            self.cal.coefs_ntwks['reverse transmission tracking'])
            
    def test_correction_accuracy(self):
        #import pdb;pdb.set_trace()
        for k in range(self.cal.nstandards):
            self.assertEqual(self.cal.apply_cal(self.cal.measured[k]),\
                self.cal.ideals[k])
    
    def test_convert_12term_2_8term(self):
        converted = rf.convert_8term_2_12term(
                    rf.convert_12term_2_8term(self.cal.coefs))
        import pdb;pdb.set_trace()
        for k in converted:
            self.assertTrue(abs(self.cal.coefs[k] - converted[k])<1e-9)
        
    


