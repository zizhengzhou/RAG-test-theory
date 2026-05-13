---
arxiv_id: "1705.09158"
title: "Suppression of 1/f noise in solid state quantum devices by surface spin desorption"
published: "2017-05-25"
authors: S. E. de Graaf, L. Faoro, J. Burnett, A. A. Adamyan, A. Ya. Tzalenchuk, S. E. Kubatkin, T. Lindström, A. V. Danilov
---

## Contents
- I Experiments
- II Results
- III Discussion
- IV Conclusions
- V Acknowledgements
- VI Author contributions
- VII Methods
- Supplemental material
  - .1 Model for interacting TLS
  - .2 Number of photons
  - .3 Power dependence of Q i subscript 𝑄 𝑖 Q_{i}
  - .4 ESR-spectrum and spin density
  - .5 CW power saturation measurements: T 1 subscript 𝑇 1 T_{1}
  - .6 Noise measurement setup: Dual Pound locking
  - .7 Loss tangent measurements
  - .8 Noise analysis
  - .9 Temperature dependence of S y subscript 𝑆 𝑦 S_{y}
  - .10 Correlated noise

## Abstract

Abstract Noise and decoherence due to spurious two-level systems (TLS) located at material interfaces is a long-standing issue in solid state quantum technologies. Efforts to mitigate the effects of TLS have been hampered by a lack of surface analysis tools sensitive enough to identify their chemical and physical nature.
Here we measure the dielectric loss, frequency noise and electron spin resonance (ESR) spectrum in superconducting resonators and demonstrate that desorption of surface spins is accompanied by an almost tenfold reduction in the frequency noise.
We provide experimental evidence that simultaneously reveals the chemical signatures of adsorbed magnetic moments and demonstrates their coupling via the electric-field degree of freedom to the resonator, causing dielectric (charge) noise in solid state quantum devices.

## I Experiments

We simultaneously measure the $1/f$ frequency noise and dielectric losses as a function of temperature and driving power (average photon number $\langle n\rangle$) of two NbN superconducting resonators (with frequencies ${\nu_{0}=4.6}$ GHz and $5.0$ GHz)aplpaper patterned on the same c-cut Al2O3 substrate.

The full high sensitivity ESR spectrum is subsequently obtained at $T=10$ mK
by measuring the quality factor of the resonator as a function of applied magnetic field and the zero field loss is subtracted to obtain the magnetic field induced loss $Q_{b}^{-1}$jap2012.
We then anneal the device at moderate temperature (300^∘C), a technique that has shown to remove some of the spins native to the surface of the devicedegraaf2017. The same noise and loss measurement protocol is repeated in a second measurement and finally the ESR spectrum is measured again, confirming the successful removal of some of the spins.
Throughout this paper we refer to these two consecutive measurements as ’before’ and ’after’ spin desorption respectively.

Figure: Figure 2: Mechanism of dielectric (frequency) noise and loss in high-Q superconducting resonators. a) A smaller number of coherent cTLS (blue) on average separated by a distance $r_{\rm cTLS}\sim 1$ $\mu$m couple to the oscillating electric field component $\vec{\mathcal{E}}$ of the resonator. Classical thermally activated TLFs (red) in $R_{0}\sim 80$ nm proximity of the cTLS generate noise while other thermally activated TLFs (grey) contribute to the cTLS line-width and the total density of TLS detected in ESR measurements. Typical distances between thermally activated TLF (at $T\sim 60$ mK) are $r_{F}\sim 100$ nm. b) TLF inside the interaction volume of the cTLS modify the tunneling potential of the cTLS, resulting in the cTLS energy drift. c) The resonantly coupled cTLS have energy level splittings near the resonance frequency $\nu_{0}$. This splitting fluctuates in time, perturbing the resonator frequency via its coupling to the electric dipole associated with the cTLS. d) The conceptual representation of the GTM where noise and loss channels are indicated (see text). The ESR measurement enables identification of TLFs via the new dissipation channel, indicated by dashed lines, arising when the spins are in resonance with the microwave field.
Refer to caption: /html/1705.09158/assets/x2.png

The frequency noise is measured in two resonators using a high precision dual Pound locking technique adapted from frequency metrologytobiaspound that continuously monitors the centre frequency of the resonators.
Values for the dielectric loss tangent $\tan\delta_{0}$ before and after annealing are extracted from quality factor measurements at low power, and from an independent measurement of the temperature-dependent frequency shift of the resonators we find the intrinsic loss tangent $\tan\delta_{i}$. For further details see Methods.

## II Results

The main result of this work is shown in Figure [1](#S0.F1). In summary, after annealing and desorption of surface spins we observe almost an order of magnitude reduction (on average 9.1 and 8.4 times for the two resonators respectively) in the frequency noise spectral density (Figure [1](#S0.F1)a-c) for both measured resonators at the lowest temperatures.

The reduction in noise is observed together with a reduction in number of surface spins.
Figures [1](#S0.F1)d and [1](#S0.F1)e display the ESR spectrum measured in-situ after collecting all the noise data, before and after annealing. The measured ESR spectrum reveals the presence of atomic hydrogen on the Al2O3 surface originating from water dissociationhass1998 and electronic charge states (with a g-factor of 2.0), likely due to absorption of oxygen radicals on the surface in accordance with previous findingsdegraaf2017; kumar2016.
An initial density of $n_{H}=2\cdot 10^{17}$ m^-2 hydrogen spins is completely removed and we extract a reduction in spin density due to the central peak from $n_{e}=0.91\cdot 10^{17}$ m^-2 to $\tilde{n}_{e}=0.17\cdot 10^{17}$ m^-2 spins/m^2, a factor of 5.3. The wide background plateau remained unchanged.

Intriguingly, in contrast to the tenfold reduction in noise, we find that the intrinsic loss tangent $\tan\delta_{i}$ is only reduced by 30% after surface spin desorption.
For each resonator we also measured the power and temperature dependence of the quality factor, from which we also see only a very small reduction in the loss (see Table [1](#S4.T1) for exact values).

## III Discussion

This small reduction in loss but large reduction in noise can be explained within the framework of strongly interacting TLS and the GTM, which naturally partitions the TLS as two distinct entities, one predominantly responsible for loss and one for noise.
The microscopic picture is the following. Associated with each TLS there is a fluctuating dipole $d_{0}$ that couples to the applied microwave electric field ${\cal E}$ from the resonator.
Among the TLS we can distinguish between coherent (quantum) electrical dipoles (cTLS) that are characterized by fast transitions between their states and relatively small decoherence rates, and slow classical fluctuators (from now on referred to as TLF) that are characterized by decoherence times shorter than the typical time between the transitions.
The picture is sketched in Figure [2](#S1.F2)a with typical distances between thermally activated (excited) cTLS and TLF as inferred from our measurements.

At low temperatures, slow fluctuators weakly coupled to cTLS mainly contribute to the dephasing of the high energy cTLS and are responsible for their line-width $\Gamma_{2}$faoro2015; lisenfeld2016. Slow fluctuators that are located close to the cTLS, and therefore are strongly coupled, shift the cTLS energy by an amount larger than $\Gamma_{2}$. These fluctuators create highly non-Gaussian noise that cannot be regarded as a contribution to the line-width. For resonant cTLS, having an energy splitting ${E\approx\hbar\nu_{0}}$, the interaction with a few strongly coupled TLF translates to the energy of the cTLS drifting in time, as illustrated in Figure [2](#S1.F2)b and c; it is this drift that ultimately generates $1/f$ noise in the resonatorfaoro2015.

The intrinsic loss (at low fields) on the other hand arises from direct phonon relaxation from the resonantly coupled cTLS, and depends only on the number of cTLS, as shown in Figure [2](#S1.F2)d.
Within the framework of the GTM our experimental findings of a small reduction in loss and a dramatic reduction in noise imply that desorption of surface spins did not affect the density of cTLS, instead the surface spins can be attributed to the TLF.

The conceptual picture of these two separate TLS communities is further supported by additional experimental findings:
for a homogeneous bath of non-interacting TLS (STM)
we expect $Q_{i}(\langle n\rangle)\sim\langle n\rangle^{\alpha}$ with $\alpha=0.5$.
The observed dependence is much weaker: a fit to a power law returns $\alpha\approx 0.2$ for both resonators before and after desorption (see Supplementary). On the other hand, for interacting TLS we do expect a weak logarithmic dependence of the microwave absorption on stored energy in the resonatorfaoro2012

$$ $\frac{1}{Q_{i}(\langle n\rangle)}=P_{\gamma}F\tan\delta_{i}\ln\left(C\sqrt{\frac{|n_{c}|}{|\langle n\rangle|}}+c_{0}\right).$ (1) $$

Here $C$ is a constant, $c_{0}$ accounts for power-independent losses, F is a geometric filling factor and $\displaystyle{P_{\gamma}}$ is a normalization factor that depends on the spectral density of TLF switching rates.
In Figure [3](#S3.F3) we show that our data fits very well to this logarithmic power dependence.

Figure: Figure 3: Resonator quality factor. Inverse internal quality factor as a function of number of photons in the 5 GHz resonator. Solid lines are fits to the logarithmic power dependence of equation ([1](#S3.E1)) for $\langle n\rangle\gtrsim 50$. Extracted values are reported in Table [1](#S4.T1).
Refer to caption: /html/1705.09158/assets/x3.png

Interestingly, we find that $P_{\gamma}$ increases after spins were removed. This implies that the remaining slow fluctuators have a narrower range of switching rates and are likely different in nature than the spins that were desorbed.

Independently, another important indication of the applicability of our model is given by the analysis of the temperature dependence of the $1/f$ noise spectrum. The interaction gives a vanishing density of states for cTLS at low energies, $P(E)\propto E^{\mu}$ with $0<\mu<1$, and this results in a scaling of the noise spectrum with temperature $S_{y}(T)\propto T^{-(1+2\mu)}$ (for ${T<h\nu_{0}/k_{B}}$). In agreement with previous studiesburnett2016; burnett2014; skacel2014; lisenfeld2010 we find ${\mu\approx 0.3}$ (see Supplemental material), both before and after spin desorption. This is further evidence that desorption only affects the number of slow TLF present on the sample.

We now combine all available data to produce a qualitative picture (as sketched in Figure [2](#S1.F2)) of the microscopic properties of the cTLS and TLF, by taking the GTM beyond the original assumptions of identical densities and dipole moments of cTLS and TLFfaoro2015; burnett2016. The details of this theory and analysis can be found in the Supplemental material, here we only summarize the results.

Assuming the dipole moment for resonant cTLS to be on the atomic scale, ${d_{0}=1\text{ e\AA}\sim 5\text{D}}$ (i.e. similar to what was previously deduced from spectroscopy measurementssarabi2016; martinis2004), we arrive at dipole-dipole interaction strength ${U_{0}\approx 15\text{ K}\text{nm}^{3}}$.
Before spin desorption, we find from the intrinsic loss tangent the cTLS line-width ${\Gamma_{2}\sim 20\text{ MHz}}$ at ${T=60\text{ mK}}$ (see Supplemental material), which translates into the density of resonant cTLS ${\rho_{TLS}\approx 15\text{ GHz}^{-1}\mu\text{m}^{-2}}$ in agreement with Ref. lisenfeld2016, where the authors found $\sim 50$ resonant cTLS per $\mu\text{m}^{2}$ in the frequency range ${3-6}$ GHz, i.e. resonant cTLS are located at a typical distance $r_{cTLS}\sim 1$ $\mu\text{m}$ from each other, similar to the densities found in qubit tunnel junctionsmartinis2004.

Next, the measured amplitude of the noise $A_{0}$ can be related to the density of thermally activated (fluctuating) TLF and their dipole moment $d_{F}$. We find $\displaystyle{\frac{d_{F}}{d_{0}}\rho_{F}\approx 5\pm 4\cdot 10^{-3}\text{ nm}^{-2}}$.
The thermally activated TLF constitutes a fraction $T/W$ of the total number of TLF, where $W$ is the bandwidth of the distribution of TLF energy level splittings. For weakly absorbed spins it is reasonable to expect that ${W\sim 100}$ K, limited by the observed desorption energy. From the total spin density measured by ESR we have ${n_{e}+n_{H}\approx 3\cdot 10^{-1}\text{ nm}^{-2}}$.

Combining these estimates, assuming all the TLFs are the observed spins, we have for the density of thermally activated TLF ${\rho_{F}=(n_{e}+n_{H})(T/W)\sim 2\cdot 10^{-4}\text{ nm}^{-2}}$ (i.e. thermally activated TLFs are separated by an average distance ${r_{F}\sim 100\text{ nm}}$) and ${d_{F}/d_{0}\sim 30\pm 25}$. The large uncertainty in $d_{F}/d_{0}$ stems from its strong dependence on the filling factor ($\propto F^{3}$) and the volume where the TLF are situated, which both cannot be accurately estimated.
However, the message of this order of magnitude estimation is that the assumption that all TLS are the observed spins is indeed plausible. Furthermore, the dipole moment of a surface TLF is likely larger compared to that of TLS in the bulk, as would be expected since the physisorbed and easily desorbed spins are likely to move larger distances.

After spin desorption the noise amplitude decreases by a factor $\sim 10$, the loss is only reduced by ${\sim 30\%}$ and the normalization constant $P_{\gamma}$ increases $\sim 65\%$ due to lower TLF switching rates. From this we can finally find a corresponding change in the density of TLF before and after spin desorption

$$ $\frac{\rho_{F}(T)}{\tilde{\rho}_{F}(T)}=\frac{A_{0}\tilde{P}_{\gamma}\tan\delta_{i}}{\tilde{A}_{0}P_{\gamma}\tan\tilde{\delta_{i}}}=15.23\quad\text{and}\quad 17.7,$ (2) $$

for the two resonators. Here we denote quantities for the ’after’ measurement by the tilde symbol. These values correlate remarkably well with the change in the total number of spins in the three ESR peaks $(n_{e}+n_{H})/\tilde{n}_{e}=17.1$ (4.6 GHz resonator), and again indicates that spins contribute to the frequency noise in our high-Q superconducting resonators and take on roles as slow (mobilehass1998) fluctuators.

## IV Conclusions

Based on the experimental evidence from the loss, noise and ESR spectrum, all obtained on the same device, we have found that surface spins that are known to give rise to magnetic noise in quantum circuitssendelbach2008; quintana2017; degraaf2017 are also responsible for the low frequency dielectric noise of the resonator. These spins, remarkably present in densities also inferred to be responsible for flux noise in SQUIDs and qubitssendelbach2008, take on roles as slow classical fluctuators that cause an energy drift of resonant coherent TLS. Removing a majority of these spins gives an almost tenfold reduction in dielectric noise.

In our device the observed surface spins constitute weakly physisorbed atomic hydrogen together with free radicals ($g=2$). We note that the nature of the $g=2$ spins is still not entirely clear. A large portion can be associated with surface adsorbates, likely oxygen radicalsdegraaf2017; kumar2016, or other light molecular adsorbentslee2014; lordi2017. The remaining fraction of free radicals may be a result of insufficient annealing or they may be of a different chemical or physical origin with much higher desorption barriers. Another possibility is that the remaining more robust localised charges and cTLS are intrinsic to the Al2O3 surface itselfdesousa2007; hass1998, more resembling ”bulk” defectsbedilo2014.
Nevertheless, our approach reveals a new aspect of the noise in solid state quantum devices as we show that observed magnetic dipoles, with their fingerprint revealed through state-of-the-art surface analysis using in-situ micro-ESR, couple via the electric field degree of freedom and give rise to dielectric noise.

Similar physics is expected for a wide range of oxide surfaces relevant for quantum technologies.
The importance of magnetic moments has previously been widely overlooked in resonators since electrical dipoles have been considered the dominating mechanism for dielectric noise. Our results instead indicate that while having a small influence on power loss, these spins (and their associated electric dipoles) constitute a major source of noise and dephasing in modern high coherence solid state devices by their proximity to coherently coupled resonant cTLS, and our results hint at a connection between the similar densities found for sources of fluxsendelbach2008, chargeastafiev2004; arsalan2014 and dielectric noise in quantum circuits.

**Table 1: Extracted parameters from ESR and noise/loss measurements. For a detailed description of each parameter see Refs. degraaf2017; burnett2016; faoro2015 and the supplemental material. ^†For the 4.6 GHz resonator. Where indicated, deviations are 95% confidence bounds or propagated errors thereof from fitting.**
| Quantity | Unit | Before | After | Note |
| --- | --- | --- | --- | --- |
| Spin density^† | $10^{17}$m^-2 | $0.91$ | $0.17$ | $g=2$ |
| $2.0$ | 0 | H |  |  |
| $F\tan\delta_{i}$ | $\times 10^{-6}$ | $10.6\pm 0.15$ | $7.44\pm 0.13$ | 4.6 GHz |
| $10.4\pm 0.27$ | $7.69\pm 0.12$ | 5.0 GHz |  |  |
| $P_{\gamma}F\tan\delta_{i}$ | $\times 10^{-6}$ | $4.2\pm 0.24$ | $4.9\pm 0.1$ | 4.6 GHz |
| $5.4\pm 0.6$ | $6.5\pm 0.6$ | 5.0 GHz |  |  |
| $P_{\gamma}$ |  | $0.39\pm 0.02$ | $0.66\pm 0.02$ | 4.6 GHz |
| $0.52\pm 0.06$ | $0.84\pm 0.08$ | 5.0 GHz |  |  |
| $\alpha$ |  | $0.20\pm 0.024$ | $0.18\pm 0.037$ | 4.6 GHz |
|  | $0.27\pm 0.02$ | $0.22\pm 0.038$ | 5.0 GHz |  |
| $2\mu$ |  | $0.64\pm 0.50$ | $0.43\pm 0.21$ | 4.6 GHz |
| $A_{0}/2\pi$ | $10^{-17}$ | $2.2\pm 0.3\cdot 10^{4}$ | $2.4\pm 0.4\cdot 10^{3}$ | 4.6 GHz |
| $1.2\pm 0.4\cdot 10^{4}$ | $1.1\pm 0.3\cdot 10^{3}$ | 5.0 GHz |  |  |

## V Acknowledgements

This work was supported by the UK government’s Department for Business, Energy and Industrial Strategy. The authors would like to thank S. Lara-Avila for assistance with fabrication. LF acknowledges support by ARO grant W911NF-13-1-0431 and by the Russian Science Foundation grant #14-42-00044. AD acknowledges support from VR grant 2016-04828.

## VI Author contributions

SdG, SK, AD, TL and AT conceived the experiment. AA prepared and treated the samples. SdG performed the noise and ESR measurements with assistance from TL. SdG analysed the data and LF articulated the theory, both with inputs from JB, AT and TL. All authors discussed the results. SdG, LF and TL wrote the manuscript with input from all authors.

## VII Methods

Sample preparation.
Sapphire substrates were annealed in situ at high temperature, $800^{\circ}$C, for 20 minutes prior to deposition of 2 nm NbN. After cooling down to $20^{\circ}$C, an additional 140 nm NbN was sputtered.
Resonators were patterned using electron beam lithography (UV60 resist, MF-CD-26 developer, DI water rinse) and subsequent reactive ion etching in a NF3 plasma. Resist was removed in 1165 remover followed by oxygen plasma treatment. Resonator designs were identical to those reported in Ref. aplpaper.
After the first round of noise measurement the same sample was warmed up, shipped from UK to Sweden, and heated in vacuum to $\sim 300^{\circ}$C for 15 minutes to desorb surface spins, then shipped back to the UK, and mounted in the same cryostat with the same noise measurement setup $\sim 72$ hours later. Remarkably, the detrimental surface spins are not re-introduced even after this time.

Measurement setup.
We used a cryogen-free dilution refrigerator with a base temperature of 10 mK and a 3-axis superconducting vector magnet for noise and ESR measurements. The cryostat was equipped with heavily attenuated coaxial lines, cryogenic isolators and a low noise high electron mobility transistor (HEMT) amplifier with a noise temperature of $\sim 4$ K. All noise measurements were performed with the leads to the vector magnet completely disconnected. Only after completion of noise measurements the magnet was connected to measure the ESR spectrum. The plane of the superconductor thin-film was found to high precision ($<0.1^{\circ}$) by applying a small field and carefully tilting the angle of the applied field while finding the maximum of the resonance frequency of the resonators.
ESR measurements were performed by sweeping the magnetic field and measuring the characteristics of the resonators using a vector network analyser.
Noise measurements were performed using a Pound locking techniquetobiaspound that tracks the resonance frequency (and its fluctuations) in real-time. For a detailed explanation of the technique, see supplemental material.

## Supplemental material

### .1 Model for interacting TLS

Our experiments on noise and loss indicate that interactions between TLS are important. They also demonstrate that while the spin desorption procedure significantly affects the magnitude of the noise it has only a minor effect on the intrinsic loss tangent. In this section we discuss the full microscopic model of interacting TLS and their physical origin that follows from the data.

The fact that surface spin removal has a small effect on the loss tangent implies that the spins do not contribute significantly to the loss at high frequency and thus are not a part of the resonant cTLS ensemble. However, the reduced noise implies that the spins are a significant host of the bath of slow fluctuating dipoles (TLF). The ESR spectrum also indicates that the desorbed spins (both H and free electron states) can be highly mobile and can tunnel a long distance, i.e. they can easily serve as the dominant fraction of slow fluctuating dipoles.

Coherent cTLS are associated with fluctuating dipoles $d_{0}$ and are described by the Hamiltonian $H_{TLS}=\frac{\Delta}{2}\sigma^{z}+\frac{\Delta_{0}}{2}\sigma^{x}$ characterized by an asymmetry $\Delta$, tunneling matrix element $\displaystyle{\Delta_{0}}$, and ${\sigma^{a},a=x,y,z}$ are the Pauli matrices. In the rotated basis, the Hamiltonian is simply $H_{TLS}=ES^{z}$, where ${E=\sqrt{\Delta^{2}+\Delta_{0}^{2}}}$ is the TLS energy splitting and $\displaystyle{S^{z}=\frac{1}{2}(\cos\theta\sigma^{z}+\sin\theta\sigma^{x})}$ with ${\tan\theta=\Delta_{0}/\Delta}$. The interaction strength is set by the dipole-dipole interaction scale ${U_{0}=d_{0}^{2}/\varepsilon_{h}}$, where $\varepsilon_{h}=10$ is the dielectric constant of the host medium. As a consequence of this interaction, the TLS density at low energies is ${P_{TLS}(E,\sin\theta)=\frac{P_{0}}{\cos\theta\sin\theta}\left(\frac{E}{E_{\rm max}}\right)^{\mu}}$, where ${\mu<1}$ is a small positive parameter. Among coherent TLS we distinguish high, ${E\gg k_{B}T}$, and low ${E\leq k_{B}T}$ (thermally activated) energy TLS. In addition, some TLS can be (near) resonant with the resonator, $E\sim h\nu_{0}$.

The slow fluctuators are represented by classical fluctuating dipoles with moment $d_{F}$, characterized by switching rates $\gamma$ with a probability distribution ${P_{F}(E,\gamma)=P_{0}^{F}/\gamma}$ and ${\gamma_{min}\ll\gamma\ll\gamma_{max}}$. Such a distribution for the switching rates appears naturally for thermally activated tunneling.

The loss in a high quality resonator is caused by fluctuating dipoles with energies close to the resonator frequency $\nu_{0}$. In the regime of low temperature, ${k_{B}T\ll h\nu_{0}}$, the resonant cTLS have a small dephasing width due to their interaction with thermally activated TLS and TLF. This width is given bysupp_faoro2015

$$ $\Gamma_{2}=\ln\left(\frac{\Gamma_{1}^{max}}{\Gamma_{1}^{min}}\right)\chi\frac{T^{1+\mu}}{\nu_{0}^{\mu}},$ (S3) $$

where ${\chi=P_{0}U_{0}\left(\frac{\nu_{0}}{E_{max}}\right)^{\mu}}\approx\tan\delta_{i}$
is a dimensionless parameter, obtained directly from loss tangent measurements, that controls the effect of the interaction on the resonant cTLS. $\Gamma_{1}^{max}$ and $\Gamma_{1}^{min}$ are the minimum and maximum relaxation rates of these cTLS respectively. Direct measurements give ${\Gamma_{1}^{max}\approx 10^{4}\text{ s}^{-1}}$ for the thermally activated cTLS at ${T\approx 35\text{ mK}}$supp_lisenfeld2016. The precise value of ${\Gamma_{1}^{min}}$ for thermally activated cTLS is not known. However, the electrical noise data shows that $1/f$ noise generated by these cTLS extends to very low frequencies ${f\leq 1\text{ mHz}}$ beyond which the dependence changes. This implies that ${\Gamma_{1}^{min}\approx 10^{-3}\text{ s}^{-1}}$, such that ${\ln\left(\Gamma_{1}^{max}/\Gamma_{1}^{min}\right)\approx 20}$.

The total number of resonant cTLS in a volume $V_{h}$ ($=2.4$ and 2.2 $\cdot 10^{-16}$ m^3 for the two resonators respectively) of host material can then be estimated from the measured loss tangent as ${{\cal N}_{res}=\frac{\chi}{U_{0}}V_{h}\Gamma_{2}}$; their average distance is ${r_{cTLS}\sim\left(\chi\Gamma_{2}/U_{0}\right)^{-1/3}}$ in bulk material and ${r_{cTLS}\sim\left(d\chi\Gamma_{2}/U_{0}\right)^{-1/2}}$ in a thin film of thickness $d\ll r_{cTLS}$.

The noise in the resonator is due to the slow TLF that interact strongly with these resonant cTLS and create highly non-Gaussian noise, that cannot be regarded as a contribution to $\Gamma_{2}$. These TLF are located at distance $r<R_{0}$, where ${R_{0}^{3}=\frac{d_{F}}{d_{0}}\frac{U_{0}}{\Gamma_{2}}}$. Their switchings bring the cTLS in and out of resonance with the resonator leading to $1/f$ frequency noise. The number of thermally activated TLF strongly coupled to a resonant cTLS is ${{\cal N}_{F}(T)=P_{0}^{F}\frac{4\pi}{3}R_{0}^{3}T}$ and their average distance is ${r_{F}\sim(P_{0}^{F}T)^{-1/3}}$. If the total number of such fluctuators, ${{\cal N}_{F}^{tot}(T)={\cal N}_{res}{\cal N}_{F}(T)\gg 1}$, the frequency noise spectrum of the resonator can be expressed as a superposition of Lorenztians generated by the switching of the TLF strongly coupled to the resonant cTLS.

In the limit of weak electric field $\vec{{\cal E}}$ we find that the noise is given bysupp_faoro2015

$$ $\frac{S_{\delta\nu}}{\nu_{0}^{2}}=\frac{8}{15}\langle d_{0}^{4}\rangle\frac{\chi}{U_{0}\Gamma_{2}}{\cal F}(\vec{{\cal E}}){\cal N}_{F}(T)\int_{\gamma_{min}}^{\gamma_{max}}\frac{\gamma P(\gamma)}{\gamma^{2}+\omega^{2}}d\gamma.$ (S4) $$

Here ${P(\gamma)=P_{\gamma}/\gamma}$ is the normalized distribution function of slow fluctuators with $\displaystyle{P_{\gamma}=\ln^{-1}[\gamma_{max}/\gamma_{min}]}$ and
$\displaystyle{{\cal F}(\vec{{\cal E}})=\frac{\int_{V_{h}}|\vec{{\cal E}}|^{4}dV}{4(\int_{V}\varepsilon_{0}|\vec{{\cal E}}|^{2}dV)^{2}}\approx\frac{F^{2}}{\varepsilon_{h}^{2}V_{h}}}$ where we introduced the filling factor $\displaystyle{F=\frac{\int_{V_{h}}\varepsilon_{h}|\vec{{\cal E}}|^{2}dV}{2\int_{V}\varepsilon_{0}|\vec{{\cal E}}|^{2}dV}}\sim 0.01-0.02$ supp_burnett2016 which accounts for the fact that the TLS host material volume $V_{h}$ may only partially fill the resonator mode volume $V$. We note that the uncertainty in accurately determining $F$ gives a large range for the possible dipole moment ratio $d_{F}/d_{0}$. The ranges given for the quantities in the discussion on $d_{F}$ in the main manuscript are the values obtained for the estimated range of the filling factor.
Notice that in this limit the noise spectrum scales with temperature as ${\propto T^{-(1+2\mu)}}$. Eq. ([S4](#Ax1.E4)) gives the $1/f$ noise spectrum

$$ $\frac{S_{\delta\nu}}{\nu_{0}^{2}}=\frac{A_{0}}{2\pi f}.$ (S5) $$

The amplitude $A_{0}$ can be expressed through the total number of thermally activated fluctuators ${{\cal N}^{\text{tot}}_{F}(T)}$ as

$$ $A_{0}\approx\pi\frac{d_{F}}{d_{0}}{\cal N}^{\text{tot}}_{F}(T)\left[\chi F^{2}P_{\gamma}\right]\left(\frac{U_{0}}{\Gamma_{2}V_{h}}\right)^{2}.$ (S6) $$

### .2 Number of photons

Figure [S1](#Ax1.F1)a shows the number of photons in the 4.6 GHz resonator vs internal loss ($Q_{i}^{-1}$) for the two measurements at two temperatures. Each measurement was made in the same sample cell using the same microwave setup, and the initial assumption is that in the two separate measurements the attenuation in the cryostat was the same. Each data point corresponds to a 2 dB increment in the applied power, both datasets starting at the same low applied power. Therefore, the range of microwave powers applied to the sample is expected to be the same across both measurements. This is further validated by the measurement of white noise levels that are the same (within a factor 2). The white noise level in these measurements is dominated by the microwave power incident on the cryogenic amplifier.

The number of photons within the resonator scales with the loaded quality factor, and therefore also with the internal quality factor. As discussed in the main text, the spin desorption leads to an increase in $Q_{i}$, meaning that for the same applied microwave power, the number of photons in the resonator is different between the ”before” and ”after” measurements. Importantly, the noise scales with both the number of photons within the resonator and with $Q_{i}$. As is consistent with the literature, we calibrate the applied power such that we compare noise for the same number of photons within the resonator.

Figure: Figure S1: Inverse internal quality factor as a function of number of photons in the resonator for two extreme temperatures covering those used in all other measurements. Each data point is an increment in applied power by 2 dB, starting at the same low applied power. Fits are to equation ([S7](#Ax1.E7)). Some of the data is the same as in Figure [3](#S3.F3).
Refer to caption: /html/1705.09158/assets/x4.png

### .3 Power dependence of Q i subscript 𝑄 𝑖 Q_{i}

For consistency we here also provide the analysis of the quality factor data within the framework of the STM. Here we expect at strong fields $\langle n\rangle\gg n_{c}$

$$ $Q_{i}^{-1}=\frac{F\tan\delta_{i}}{(1+\langle n\rangle/n_{c})^{\alpha}}+Q_{i,0}^{-1},$ (S7) $$

where the constant $Q_{i,0}$ accounts for power-independent loss and $n_{c}$ is a critical photon number for saturation, ${\alpha=0.5}$ and $F$ is the filling factor of the TLS hosting medium in the resonator. By fitting the measured $Q_{i}(\langle n\rangle)$ to this power law we find $\alpha\sim 0.2$ both before and after spin desorption. Typical fits can be seen in Figure [S1](#Ax1.F1).

### .4 ESR-spectrum and spin density

The ESR-spectrum in Figure [1](#S0.F1) is obtained by measuring the transmitted microwave signal, $S_{21}$, around resonance as a function of applied magnetic field using a vector network analyser.
All noise measurements were performed first, making sure the resonator was not poisoned by vortices. Once noise measurements were completed, the superconducting magnet leads were connected and a magnetic field applied in the plane of the superconducting film. The measured microwave transmission was fitted tosupp_khalil2013

$$ $S_{21}=1-\frac{(1-S_{21,{\rm min}})e^{i\varphi}}{1+2iQ\frac{\nu_{0}-f}{\nu_{0}}},$ (S8) $$

to extract the internal quality factor $Q_{i}=Q/S_{21,{\rm min}}$. The parameter $\varphi$ accounts for the asymmetry in the resonance line-shape accounting for possible impedance mismatch. The spin-induced loss is then calculated as $Q_{b}^{-1}(B)=Q_{i}^{-1}(B)-Q_{i}^{-1}(B=0)$.
We fit the ESR-spectrum to a model of two coupled oscillators to extract the collective coupling, $\Omega$, and line width $\gamma_{2}$ ($=1/T_{2}$ for a Lorentzian ESR peak) of the spin system.

$$ $S_{21}(\omega)=1+\frac{\kappa_{c}}{i(\omega-\omega_{0})-\kappa+\frac{\Omega^{2}}{i(\omega-\omega_{s})-\gamma_{2}/2}},$ (S9) $$

Eq. [S9](#Ax1.E9) here describes the central $g=2$ peak only and $\omega_{0}=2\pi\nu_{0}$ and $\omega_{s}=g\mu_{B}B/\hbar$ is the angular resonance frequency and induced Zeeman splitting of the spins respectively, and $\kappa_{(c)}=\omega_{0}/Q_{(c)}$.
From the collective coupling $\Omega$ we can evaluate the surface spin density based on the geometry of the resonatorsupp_degraaf2017. Comparing the same resonator before and after annealing also gives a direct measure of the relative reduction in spin density independent of resonator geometry via the observed reduction in collective coupling of the spins, $\Omega\propto\sqrt{n}$. In the ’After’ measurement we have removed $\sim 2\cdot 10^{17}$ Hydrogen spins$/$m^2 and the density of $g=2$ spins was reduced 5.3 times to $\sim 0.17\cdot 10^{17}$ spins$/$m^2. Figure [1](#S0.F1)e shows the good agreement of the ESR data to theory.
We note that the reduction of 5.3 times is larger than previously observedsupp_degraaf2017, suggesting that the $g=2$ spins have a larger desorption energy than the hydrogen.

### .5 CW power saturation measurements: T 1 subscript 𝑇 1 T_{1}

Figure: Figure S2: Spin relaxation times. a) CW power saturation measurements at three different temperatures showing the normalised inverse dissipation into the spin system as a function of circulating power in the 4.6 GHz resonator after annealing. b) the extracted (from fits) relaxation time $T_{1}$ as a function of temperature for the $g=2$ peak. Solid line is $1/T$.
Refer to caption: /html/1705.09158/assets/x5.png

When evaluating the spin density it is essential to ensure that the spin ensemble is not saturated by the microwave signal in the resonator. To verify this we measure the ESR-spectrum at a wide set of applied powers and extract the dissipation into the spin system at the $g=2$ peak as a function of circulating power in the resonator. The result for one such measurement (after annealing, evaluated for the $g=2$ peak) is shown in Figure [S2](#Ax1.F2)a for three different temperatures.
The method to evaluate $Q_{s}$ is described in Ref. supp_degraaf2017 together with the methodology used to extract the spin relaxation time $T_{1}$ plotted versus temperature in Figure [S2](#Ax1.F2)b. Interestingly we find a $T^{-1}$ dependence of the relaxation time, a signature of direct spin-lattice relaxation as the dominant mechanism for spin energy relaxationsupp_schweiger. Direct phonon relaxation and a $T_{1}\propto T^{-1}$ dependence is also the dominant mechanism for TLS relaxation in amorphous glasses at low temperatures, well captured by both the STM and the GTMsupp_faoro2015, predicting a similar dominating phonon relaxation time in the ms range.

We note that spin desorption does not change $T_{1}$, while the electron spin dephasing time $T_{2}$ inferred from the transition line-width increases marginally (table [1](#S4.T1)), an indication of reduced spin-spin induced decoherence, alternatively the remaining spins could be of a different nature.

### .6 Noise measurement setup: Dual Pound locking

The measurement setup we use is a further development of the Pound locking techniquesupp_tobiaspound for microwave resonators. This modification allows us to simultaneously measure the frequency noise in two different resonators, increasing the amount of data collected and allowing for measurement of correlated noise.

Figure: Figure S3: Dual Pound-locking measurement setup. For details see text.
Refer to caption: /html/1705.09158/assets/x6.png

Pound locking is a highly accurate technique to directly measure frequency noise of microwave oscillators.
This as opposed to measuring the phase noise $S_{\varphi}$ using a homo/heterodyne techniquesupp_barendsnoisepaper. The advantage is that we gain in sensitivity and the measurement does not suffer from additional complications such as the Leeson effect, and it is especially useful in cryogenic environments, where homo- or heterodyne techniques suffer from a wide range of fluctuations, such as in electrical length in each of the two measurement paths (signal and reference), and thermal fluctuations. The Pound locking technique instead sends the signal and reference through the same physical transmission line, where the reference takes the form of a phase modulated spectrum on top of the signal, making the measurement insensitive to first order in any variations in electrical length. The phase modulation frequency is recovered by a non-linear detector (here a diode) and any deviations in the signal frequency from the resonator frequency causes a beating at the phase modulation frequency. This beating is nulled using a lock-in in series with a PID controller which adjusts the signal frequency sent out by the microwave generator to match the instant resonance frequency.

Instead of a single Pound loop we here run two loops in parallel, as shown in Figure [S3](#Ax1.F3). Each loop, A and B, works in the same way as described in detail in Ref. supp_tobiaspound, locked to the 4.6 and 5.0 GHz resonator respectively. The microwave signals from each loop are combined and sent through the same transmission line in the cryostat, and later selectively split to each arm using 7th order tunable YIG filters with a bandwidth of $40$ MHz tuned to each respective resonance frequency. This type of multiplexed setup in principle allows for an arbitrary number of Pound loops in parallel without introducing any cross-coupling and errors in frequency measurement, as long as the YIG filters can selectively isolate the phase modulation spectrum from each measured resonator.

The power applied in each Pound loop was carefully verified using a spectrum analyser and adjusted to be equal in the two measurements, both for power incident on the resonators and power incident on the detector diode.

### .7 Loss tangent measurements

Figure: Figure S4: Intrinsic loss tangent. Frequency shift of the resonators as a function of temperature and fits to Eq. ([S10](#Ax1.E10)) (black lines). For both resonators we observe a reduction in loss tangent upon surface spin desorbtion by 25-30%. Extracted values for $\tan\delta_{i}$ are shown in Table 1. Curves are offset for clarity.
Refer to caption: /html/1705.09158/assets/x7.png

To obtain the loss tangent we measure the frequency shift of each resonator while slowly ramping up the temperature of the cryostat over the course of $\sim 120$ minutes. The frequency is measured using the Pound-loop. The loss tangent $\tan\delta_{i}$ is then extracted from fits of the $\nu_{0}(T)$ data to the STM (and GTM).

$$ $\displaystyle\delta\nu(T)$ $\displaystyle=$ $\displaystyle F\tan\delta\bigg{[}{\rm Re}\bigg{(}\Psi(\frac{1}{2}+\frac{\nu_{0}h}{2\pi ik_{B}T})$ (S10) $\displaystyle+\Psi(\frac{1}{2}+\frac{\nu_{0}h}{2\pi ik_{B}T_{0}})-\ln\frac{T}{T_{0}}\bigg{)}\bigg{]}.$ $$

Here $\delta\nu(T)=(\nu_{0}-\nu(T))/\nu_{0}$, $\Psi$ is the di-gamma function and $T_{0}$ is a reference temperature. The measured data and fits to Eq. ([S10](#Ax1.E10)) are shown in Figure [S4](#Ax1.F4). Extracted parameters are shown in Table [1](#S4.T1).

### .8 Noise analysis

Figure: Figure S5: Reduction of noise due to spin desorption. Frequency noise power spectral density $S_{y}(f)=S_{\delta\nu}(f)/\nu_{0}^{2}$ at $f=0.1$ Hz for the a) $\nu_{0}=4.6$ GHz resonator (same data as in Figure [1](#S0.F1)a) and b) the 5.0 GHz resonator. Red solid markers are before, and blue hollow markers are after spin desorption respectively. Shaded regions are a guide for the eye.
Refer to caption: /html/1705.09158/assets/x8.png

The sampled frequency vs time signal recorded from the Pound loop is converted to frequency noise spectral density $S_{y}$ by calculating the overlapping Allan-variance $\sigma_{y}^{2}(\tau)$ (AVAR) for M discrete samplings $f_{k}(n\tau)$ at multiples $n$ of the sampling rate $\tau$.

$$ $\sigma_{y}^{2}(n\tau)=\frac{1}{2(M-1)}\sum_{k=1}^{M-1}(f_{k+1}-f_{k})^{2}$ (S11) $$

For $1/f$ noise the spectral density $S_{y}(f)=h_{-1}/f$ relates to the Allan variance $\sigma_{y}^{2}=2\ln{(2)}h_{-1}$ via the coefficient $h_{-1}$ rubiola.
The AVAR is evaluated at several time-scales $t=n\tau$ ranging from 20 to 80 seconds, well within the 1/f noise limit, and the average value for $h_{-1}$ is obtained with high statistical significance. Error bars are calculated from the standard deviation of the multiple evaluations of the AVAR in the same time interval. Each datapoint in Figure [1](#S0.F1) is the result of a 2.8 hours long measurement, collecting $10^{5}$ samples without interruption at a rate $\tau^{-1}=10$ Hz. Such long measurement times are required to obtain statistically significant results for $h_{-1}$ since the $1/f$ noise in these high-Q resonators is only exceeding the system white noise level at frequencies below $\sim 1-0.1$ Hz, in particular at high temperatures and low applied powers and especially in the ’After’ measurement where the $1/f$ noise level is significantly lower.

Full data for both resonators measured is shown in Figure [S5](#Ax1.F5).

### .9 Temperature dependence of S y subscript 𝑆 𝑦 S_{y}

To extract $\mu$ we measure the temperature dependence of $S_{y}$, which in the low power and low temperature limit is expected to scale as $S_{y}(T)\propto A_{\mu}T^{-(1+2\mu)}$. The low temperature limit is given by $T<h\nu/k_{B}\approx 220$ mK for our $\nu=4.6$ GHz resonator. This measurement and fits to extract $\mu$ are shown in Figure [S6](#Ax1.F6). Confidence intervals given for $\mu$ are propagated error bars from the calculation of $S_{y}$. Indeed we find $\mu>0$ for both measurements and whilst error bars are relatively large, we conclude that interaction is still present and $\mu$ has not changed by a significant amount. We do not have data at low enough photon numbers to accurately evaluate $\mu$ for the 5 GHz resonator.

Figure: Figure S6: Temperature dependence of the noise power spectral density at $\langle N\rangle=8\pm 2$ before and $\langle N\rangle=4\pm 2$ after surface spin desorption. Solid lines are fits to $S_{y}(T)=A_{0}T^{-(1+2\mu)}$. Before annealing we find $2\mu=0.64\pm 0.50$ while after annealing $2\mu=0.43\pm 0.21$. Due to thermal saturation, data points below 70 mK are excluded from the fit. We also only consider the low temperature regime $k_{B}T<\hbar\omega_{0}\approx 220$ mK.
Refer to caption: /html/1705.09158/assets/x9.png

### .10 Correlated noise

To rule out external factors, such as system noise, magnetic field or thermal fluctuations, vibrations, and vortices influencing the results we verify that the measured $1/f$ noise is local to each resonator by measuring their correlated noise. We evaluate the correlated noise as the coherence function from the spectral densities

$$ $C=\frac{|S_{AB}|^{2}}{S_{AA}S_{BB}}.$ (S12) $$

Here $S_{XY}$ is the cross-power spectral density

$$ $S_{XY}=\int_{-\infty}^{\infty}dte^{-i\omega t}\int_{-\infty}^{\infty}d\tau\nu_{X}(\tau)\nu_{Y}(t+\tau)$ (S13) $$

of frequency fluctuations $\nu_{A}(t)$ and $\nu_{B}(t)$, where A and B denote the two different resonators.
Figure [S7](#Ax1.F7) shows the measured coherence $C(0.1{\rm Hz})$ as a function of temperature and for the two extreme powers applied to each resonator, obtained from the same data as in Figure [S5](#Ax1.F5). We observe no correlations at the time-scale of 0.1 Hz that is relevant for the $1/f$ noise analysis performed in this work.

Figure: Figure S7: Uncorrelated noise. The coherence (normalised correlation) at 0.1 Hz between simultaneously measured 4.6 and 5.0 GHz resonators. The measurement shows that the 1/f noise in each resonator at the time-scale of 0.1 Hz is dominated by local sources at all relevant temperatures. Low power is equivalent to $\langle N\rangle\sim 1-10$ and high power corresponds to $\langle N\rangle\sim 10^{3}-10^{4}$.
Refer to caption: /html/1705.09158/assets/x10.png

As another control experiment we measured the coherence while applying a weak (0.02 mT) external magnetic field perpendicular to the superconducting thin-film plane of the sample at a frequency of 0.2 Hz. The measured coherence is very strong at this particular frequency and its higher harmonics, as shown in Figure [S8](#Ax1.F8). These measurements clearly verify that we have successfully eliminated any common sources of noise and the dominating contribution to the $1/f$ noise originates from noise sources local to each resonator within the entire measurement space presented in this work.

Figure: Figure S8: Correlated noise due to external perturbation. a) Power spectral density of frequency fluctuations in the two resonators (before spin desorption, at $T=20$ mK) when a small oscillating magnetic field at 0.2 Hz is applied to the sample. The coherence data for the same measurement as in a) and another measurement when the field modulation is turned off. The amplitude of field fluctuations was $0.1$ Oe resulting in approximately 20 kHz oscillations in the resonance frequencies of the resonators.
Refer to caption: /html/1705.09158/assets/x11.png