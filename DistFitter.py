class DistFitter():
    # TODO: Allow for both method of moments (MoM) and maximum likelihood estimator (MLE) fitting approaches.
    def __init__(self, fittingData, fittingSettings):
        self.data = fittingData
        self.fittingSettings = fittingSettings

