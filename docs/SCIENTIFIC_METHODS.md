# Scientific & Mathematical Methods Reference
## Cardiac Deformation Lab (v1.0.4)
### Image-Based Computational Biomechanical Motion & Strain Analysis

---

> [!WARNING]
> **RESEARCH PROTOTYPE NOTICE & SCIENTIFIC DISCLAIMER**  
> This software is a computational research prototype designed solely for engineering validation, algorithmic research, and educational demonstration. It is **NOT** a medical device, clinical diagnostic workstation, or patient monitoring system. Optical-flow-derived displacement maps represent **apparent image motion** in two dimensions and do **not** automatically establish true physical tissue motion. Results must never be used for clinical decision-making, medical diagnosis, or patient care.

---

## 1. Continuum Mechanics & Deformation Fundamentals

In continuum mechanics, the motion of a deformable body is characterized by a mapping $\boldsymbol{\chi}$ that transforms material points from an initial reference configuration $\boldsymbol{X} \in \Omega_0$ at time $t_0$ to a spatial deformed configuration $\boldsymbol{x} \in \Omega_t$ at time $t$:

$$\boldsymbol{x} = \boldsymbol{\chi}(\boldsymbol{X}, t) = \boldsymbol{X} + \boldsymbol{d}(\boldsymbol{X}, t)$$

where $\boldsymbol{d}(\boldsymbol{X}, t) = [u(X, Y), v(X, Y)]^T$ is the two-dimensional displacement vector field.

### 1.1 The Deformation Gradient Tensor

The spatial deformation gradient tensor $\boldsymbol{F}$ is defined as the Jacobian matrix of the motion mapping:

$$\boldsymbol{F} = \frac{\partial \boldsymbol{x}}{\partial \boldsymbol{X}} = \boldsymbol{I} + \nabla \boldsymbol{d} = \begin{bmatrix} 1 + \frac{\partial u}{\partial X} & \frac{\partial u}{\partial Y} \\ \frac{\partial v}{\partial X} & 1 + \frac{\partial v}{\partial Y} \end{bmatrix}$$

where $\boldsymbol{I}$ is the second-order identity tensor and $\nabla \boldsymbol{d}$ is the displacement gradient tensor.

### 1.2 Green-Lagrangian Strain Tensor

For arbitrary or finite deformations, the Green-Lagrangian strain tensor $\boldsymbol{E}$ captures geometric non-linearities:

$$\boldsymbol{E} = \frac{1}{2} (\boldsymbol{F}^T \boldsymbol{F} - \boldsymbol{I}) = \frac{1}{2} \left( \nabla \boldsymbol{d} + (\nabla \boldsymbol{d})^T + (\nabla \boldsymbol{d})^T \nabla \boldsymbol{d} \right)$$

### 1.3 Infinitesimal (Cauchy / Small-Deformation) Strain Tensor

Under the assumption of small displacements and small deformation gradients ($\|\nabla \boldsymbol{d}\| \ll 1$), the quadratic product $(\nabla \boldsymbol{d})^T \nabla \boldsymbol{d}$ is negligibly small and the strain is linearized into the Cauchy infinitesimal strain tensor $\boldsymbol{\varepsilon}$:

$$\boldsymbol{\varepsilon} = \frac{1}{2} \left( \nabla \boldsymbol{d} + (\nabla \boldsymbol{d})^T \right)$$

In Cartesian components $(x, y)$:

$$\boldsymbol{\varepsilon} = \begin{bmatrix} \varepsilon_{xx} & \varepsilon_{xy} \\ \varepsilon_{yx} & \varepsilon_{yy} \end{bmatrix} = \begin{bmatrix} \frac{\partial u}{\partial x} & \frac{1}{2}\left(\frac{\partial u}{\partial y} + \frac{\partial v}{\partial x}\right) \\ \frac{1}{2}\left(\frac{\partial u}{\partial y} + \frac{\partial v}{\partial x}\right) & \frac{\partial v}{\partial y} \end{bmatrix}$$

- **$\varepsilon_{xx}$ (Normal Strain in $x$)**: Local fractional elongation or shortening along the horizontal image axis:
  $$\varepsilon_{xx} = \frac{\partial u}{\partial x}$$
- **$\varepsilon_{yy}$ (Normal Strain in $y$)**: Local fractional elongation or shortening along the vertical image axis:
  $$\varepsilon_{yy} = \frac{\partial v}{\partial y}$$
- **$\varepsilon_{xy} = \varepsilon_{yx}$ (Engineering Shear Strain $\gamma_{xy} = 2\varepsilon_{xy}$)**: Local angular distortion between initially orthogonal line elements:
  $$\varepsilon_{xy} = \frac{1}{2} \left( \frac{\partial u}{\partial y} + \frac{\partial v}{\partial x} \right)$$

---

## 2. Invariant & Principal Strain Formulations

Tensor components $\varepsilon_{xx}, \varepsilon_{yy}, \varepsilon_{xy}$ depend upon the choice of coordinate axes. To quantify coordinate-independent physical deformations, the eigenvalue decomposition of $\boldsymbol{\varepsilon}$ yields the **principal strains**.

### 2.1 Principal Strains ($\varepsilon_1, \varepsilon_2$)

Solving the characteristic equation $\det(\boldsymbol{\varepsilon} - \lambda \boldsymbol{I}) = 0$:

$$\lambda^2 - (\varepsilon_{xx} + \varepsilon_{yy})\lambda + (\varepsilon_{xx}\varepsilon_{yy} - \varepsilon_{xy}^2) = 0$$

The roots represent the extreme normal strains:

$$\varepsilon_1 = \frac{\varepsilon_{xx} + \varepsilon_{yy}}{2} + \sqrt{\left(\frac{\varepsilon_{xx} - \varepsilon_{yy}}{2}\right)^2 + \varepsilon_{xy}^2} \quad \text{(Maximum Principal / Tensile Strain)}$$

$$\varepsilon_2 = \frac{\varepsilon_{xx} + \varepsilon_{yy}}{2} - \sqrt{\left(\frac{\varepsilon_{xx} - \varepsilon_{yy}}{2}\right)^2 + \varepsilon_{xy}^2} \quad \text{(Minimum Principal / Compressive Strain)}$$

The principal orientation angle $\theta_p$ defines the direction of maximum extension:

$$\theta_p = \frac{1}{2} \arctan\left( \frac{2\varepsilon_{xy}}{\varepsilon_{xx} - \varepsilon_{yy}} \right)$$

### 2.2 Maximum In-Plane Shear Strain ($\gamma_{\max}$)

The maximum shear strain occurs at $45^\circ$ to the principal axes:

$$\gamma_{\max} = \frac{\varepsilon_1 - \varepsilon_2}{2} = \sqrt{\left(\frac{\varepsilon_{xx} - \varepsilon_{yy}}{2}\right)^2 + \varepsilon_{xy}^2}$$

### 2.3 Equivalent (von Mises) Strain ($\varepsilon_{eq}$)

To aggregate multi-axial deformation intensity into a single positive scalar invariant analogous to the von Mises yield criterion:

$$\varepsilon_{eq} = \sqrt{\frac{2}{3} \left( \varepsilon_{xx}^2 + \varepsilon_{yy}^2 + 2\varepsilon_{xy}^2 \right)}$$

### 2.4 Volumetric Strain / Planar Area Change ($\varepsilon_{vol}$)

The trace of the infinitesimal strain tensor represents the relative local area dilatation (volume change in 2D projection):

$$\varepsilon_{vol} = \text{tr}(\boldsymbol{\varepsilon}) = \varepsilon_{xx} + \varepsilon_{yy} = \varepsilon_1 + \varepsilon_2$$

---

## 3. Curvilinear (Radial & Circumferential) Deformation

Myocardial fibers in the left ventricle undergo radial thickening and circumferential shortening. When a ventricular centroid $(x_c, y_c)$ is defined, local Cartesian displacements and strains are transformed into polar cylindrical coordinates $(r, \theta)$.

### 3.1 Polar Coordinate Definition

For any pixel $(x, y)$:

$$r = \sqrt{(x - x_c)^2 + (y - y_c)^2}, \quad \theta = \arctan2(y - y_c, x - x_c)$$

The local radial unit vector $\boldsymbol{e}_r$ points outward from the centroid, and the circumferential unit vector $\boldsymbol{e}_\theta$ points tangentially counter-clockwise:

$$\boldsymbol{e}_r = \begin{bmatrix} \cos\theta \\ \sin\theta \end{bmatrix}, \quad \boldsymbol{e}_\theta = \begin{bmatrix} -\sin\theta \\ \cos\theta \end{bmatrix}$$

### 3.2 Transformed Displacement Components

Projecting the displacement vector $\boldsymbol{d} = [u, v]^T$:

$$d_r = \boldsymbol{d} \cdot \boldsymbol{e}_r = u \cos\theta + v \sin\theta \quad \text{(Radial displacement)}$$

$$d_\theta = \boldsymbol{d} \cdot \boldsymbol{e}_\theta = -u \sin\theta + v \cos\theta \quad \text{(Circumferential displacement)}$$

### 3.3 Radial & Circumferential Strain Transformation

Using the standard 2D rotation tensor $\boldsymbol{R}(\theta) = \begin{bmatrix} \cos\theta & \sin\theta \\ -\sin\theta & \cos\theta \end{bmatrix}$:

$$\boldsymbol{\varepsilon}_{\text{polar}} = \boldsymbol{R} \boldsymbol{\varepsilon} \boldsymbol{R}^T = \begin{bmatrix} \varepsilon_{rr} & \varepsilon_{r\theta} \\ \varepsilon_{\theta r} & \varepsilon_{\theta\theta} \end{bmatrix}$$

- **Radial Strain ($\varepsilon_{rr}$)**:
  $$\varepsilon_{rr} = \varepsilon_{xx} \cos^2\theta + \varepsilon_{yy} \sin^2\theta + 2\varepsilon_{xy}\sin\theta\cos\theta$$
  *(Positive values indicate radial thickening; negative values indicate radial thinning).*

- **Circumferential Strain ($\varepsilon_{\theta\theta}$)**:
  $$\varepsilon_{\theta\theta} = \varepsilon_{xx} \sin^2\theta + \varepsilon_{yy} \cos^2\theta - 2\varepsilon_{xy}\sin\theta\cos\theta$$
  *(Negative values indicate circumferential contraction/shortening; positive values indicate stretching).*

- **Shear Strain ($\varepsilon_{r\theta}$)**:
  $$\varepsilon_{r\theta} = -(\varepsilon_{xx} - \varepsilon_{yy}) \sin\theta\cos\theta + \varepsilon_{xy}(\cos^2\theta - \sin^2\theta)$$

---

## 4. Optical Flow & Motion Estimation

The Cardiac Deformation Lab computes dense displacement fields using two-frame and multi-frame optical flow algorithms.

### 4.1 Brightness Constancy Assumption

Optical flow assumes that the pixel intensity $I(x, y, t)$ of a moving physical pattern remains constant over an infinitesimal time step $\delta t$:

$$I(x + \delta x, y + \delta y, t + \delta t) \approx I(x, y, t)$$

Linearizing via Taylor series expansion:

$$\frac{\partial I}{\partial x} u + \frac{\partial I}{\partial y} v + \frac{\partial I}{\partial t} = 0 \iff \nabla I \cdot \boldsymbol{d} + I_t = 0$$

Because this scalar equation contains two unknowns $(u, v)$ per pixel (the classical **Aperture Problem**), spatial regularization or local parametric models are required.

### 4.2 Farnebäck Polynomial Expansion Method

The primary dense motion estimator in the platform is Gunnar Farnebäck’s two-frame algorithm. The neighborhood of each pixel in both frames $f_1, f_2$ is modeled by quadratic polynomial surfaces:

$$f_1(\boldsymbol{x}) \approx \boldsymbol{x}^T \boldsymbol{A}_1 \boldsymbol{x} + \boldsymbol{b}_1^T \boldsymbol{x} + c_1$$

$$f_2(\boldsymbol{x}) \approx (\boldsymbol{x} - \boldsymbol{d})^T \boldsymbol{A}_1 (\boldsymbol{x} - \boldsymbol{d}) + \boldsymbol{b}_1^T (\boldsymbol{x} - \boldsymbol{d}) + c_1$$

Equating coefficients yields a linear system for the local displacement $\boldsymbol{d}(\boldsymbol{x})$:

$$2 \boldsymbol{A}(\boldsymbol{x}) \boldsymbol{d}(\boldsymbol{x}) = -(\boldsymbol{b}_2(\boldsymbol{x}) - \boldsymbol{b}_1(\boldsymbol{x}))$$

where $\boldsymbol{A} = \frac{\boldsymbol{A}_1 + \boldsymbol{A}_2}{2}$. The solution is integrated across Gaussian-weighted spatial neighborhoods in a multi-resolution image pyramid to capture both large coarse excursions and fine myocardial variations.

### 4.3 Lucas-Kanade Pyramidal Feature Tracking

For Region of Interest (ROI) tracking across temporal cine loops, iterative Lucas-Kanade optical flow with spatial pyramids is utilized to track landmark vertices and bounding geometries without drift accumulation.

---

## 5. Region of Interest (ROI) & Masking Mathematics

Analyses can be constrained to specific myocardial zones using geometric or freeform regions:

1. **Rectangular ROI**:
   $$\Omega_{\text{rect}} = \{ (x, y) \mid x_0 \le x \le x_0 + w, \; y_0 \le y \le y_0 + h \}$$
2. **Elliptical ROI**:
   $$\Omega_{\text{ellipse}} = \left\{ (x, y) \;\middle|\; \frac{(x - x_c)^2}{a^2} + \frac{(y - y_c)^2}{b^2} \le 1 \right\}$$
3. **Polygonal / Freehand Contour**:
   $$\Omega_{\text{poly}} = \{ (x, y) \mid \text{winding\_number}((x, y), \mathcal{P}) \neq 0 \}$$

Inside any mask $\Omega$, spatial statistics are computed over valid pixels $N = |\Omega|$:

$$\bar{m} = \frac{1}{N} \sum_{(x, y) \in \Omega} m(x, y), \quad \sigma_m = \sqrt{\frac{1}{N} \sum_{(x, y) \in \Omega} (m(x, y) - \bar{m})^2}$$

---

## 6. Spatial Calibration & Dimensional Scaling

When pixel-to-millimeter spacing ($s_x, s_y$ in $\text{mm/pixel}$) and temporal frame interval ($\Delta t$ in seconds) are specified:

- **Calibrated Displacement**:
  $$u_{\text{mm}}(x, y) = u(x, y) \cdot s_x, \quad v_{\text{mm}}(x, y) = v(x, y) \cdot s_y$$
  $$\|\boldsymbol{d}\|_{\text{mm}} = \sqrt{u_{\text{mm}}^2 + v_{\text{mm}}^2}$$
- **Calibrated Velocity**:
  $$\boldsymbol{v}(x, y) = \frac{\boldsymbol{d}_{\text{mm}}(x, y)}{\Delta t} \quad [\text{mm/s}]$$
- **Strain Scale Invariance**:
  $$\varepsilon_{xx} = \frac{\partial u_{\text{mm}}}{\partial x_{\text{mm}}} = \frac{\partial (u \cdot s_x)}{\partial (x \cdot s_x)} = \frac{\partial u}{\partial x}$$
  Strain remains dimensionless ($[-]$ or $\%$) under uniform isotropic scaling, but directional gradients scale correctly under anisotropic pixel spacing.

---

## 7. Automated Computational Quality Control (QC) Architecture

The QC service evaluates technical analysis fidelity via a multi-metric composite scoring model scaled to $[0, 100]$:

$$S_{\text{QC}} = \sum_{k=1}^K w_k \cdot s_k, \quad \sum_{k=1}^K w_k = 1.0$$

The component sub-indices include:
1. **Image Contrast & Dynamic Range ($s_{\text{contrast}}$)**: Shannon entropy and intensity variance of input frames.
2. **Motion Magnitude & Dispersion ($s_{\text{disp}}$)**: Detection of null motion ($< 0.1 \text{ px}$) or unrealistic unphysical velocities ($> 100 \text{ px}$).
3. **Flow Coherence ($s_{\text{flow}}$)**: Cosine similarity between neighboring displacement vectors.
4. **Strain Gradient Regularity ($s_{\text{strain}}$)**: Bounded derivative of spatial strain tensors to penalize noise spikes.
5. **Mask / Coverage Integrity ($s_{\text{mask}}$)**: Ratio of evaluated pixels to field-of-view; absence of NaN / Inf elements.
6. **Calibration Completeness ($s_{\text{calib}}$)**: Presence of verified physical calibration spacing.
7. **Temporal Monotonicity ($s_{\text{temp}}$)**: Frame-to-frame continuity in cine loop sequences.
8. **Speckle / Noise Assessment ($s_{\text{noise}}$)**: High-frequency spatial noise estimation via Laplacian variance.

Categories assigned:
- **Optimal / High Quality** ($S_{\text{QC}} \ge 80$)
- **Acceptable / Moderate Quality** ($60 \le S_{\text{QC}} < 80$)
- **Questionable / Low Quality** ($40 \le S_{\text{QC}} < 60$)
- **Suboptimal / Reject** ($S_{\text{QC}} < 40$)

---

## 8. Synthetic Phantom Generator & Quantitative Benchmark

To validate numerical accuracy in the absence of in-vivo ground truth, the platform provides an exact analytic phantom deformation engine.

### 8.1 Analytic Ground-Truth Transformation

Given a synthetic radial/annular texture $I_{\text{ref}}(X, Y)$, an analytical deformation field is imposed:

$$\boldsymbol{d}_{\text{GT}}(X, Y) = \begin{bmatrix} u_{\text{GT}}(X, Y) \\ v_{\text{GT}}(X, Y) \end{bmatrix} = \begin{bmatrix} \alpha X \cos\omega t - \beta Y \sin\omega t \\ \alpha Y \cos\omega t + \beta X \sin\omega t \end{bmatrix}$$

Analytical strain components are derived by exact symbolic differentiation:

$$\varepsilon_{xx,\text{GT}} = \frac{\partial u_{\text{GT}}}{\partial X} = \alpha \cos\omega t$$

$$\varepsilon_{yy,\text{GT}} = \frac{\partial v_{\text{GT}}}{\partial Y} = \alpha \cos\omega t$$

$$\varepsilon_{xy,\text{GT}} = \frac{1}{2}\left( \frac{\partial u_{\text{GT}}}{\partial Y} + \frac{\partial v_{\text{GT}}}{\partial X} \right) = 0$$

### 8.2 Quantitative Error Metrics

Estimated motion $\hat{\boldsymbol{d}}$ and strain $\hat{\boldsymbol{\varepsilon}}$ are compared to analytical ground truth:

- **Endpoint Error (EPE)**:
  $$\text{EPE} = \frac{1}{N} \sum_{i=1}^N \sqrt{(u_i - u_{\text{GT},i})^2 + (v_i - v_{\text{GT},i})^2}$$
- **Root-Mean-Square Error (RMSE)**:
  $$\text{RMSE}(\varepsilon) = \sqrt{\frac{1}{N} \sum_{i=1}^N (\hat{\varepsilon}_i - \varepsilon_{\text{GT},i})^2}$$
- **Mean Absolute Error (MAE)**:
  $$\text{MAE}(\varepsilon) = \frac{1}{N} \sum_{i=1}^N |\hat{\varepsilon}_i - \varepsilon_{\text{GT},i}|$$

---

## 9. References & Theoretical Lineage

1. **Farnebäck, G.** (2003). *Two-frame motion estimation based on polynomial expansion*. Image Analysis, Lecture Notes in Computer Science, 2749, 363-370.
2. **Lucas, B. D., & Kanade, T.** (1981). *An iterative image registration technique with an application to stereo vision*. Proceedings of Imaging Understanding Workshop, 121-130.
3. **Fung, Y. C.** (1993). *Biomechanics: Mechanical Properties of Living Tissues*. Springer-Verlag.
4. **Holzapfel, G. A.** (2000). *Nonlinear Solid Mechanics: A Continuum Approach for Engineering*. John Wiley & Sons.
5. **D’hooge, J., et al.** (2000). *Two-dimensional myocardial strain estimation with ultrasound: a feasibility study*. IEEE Trans Ultrason Ferroelectr Freq Control, 47(4), 1079-1081.

