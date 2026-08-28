Camera sets you can pick from. Each file is a drop-in replacement for
templates/cameras.txt:

  cp templates/cameras/rostrum-2d.txt templates/cameras.txt        # all songs
  cp templates/cameras/handheld-doc.txt songs/<name>/_source/cameras.txt   # one song

Then re-run `mvkit build <song>`. __GLOSSARY.txt is the vocabulary these files draw
on - read it before writing your own.

What H3 actually honours (from MiniMax's own guidance, verified against the
node's constraints):

  - Camera moves are bracket commands: [Push in] [Pull out] [Pan left]
    [Pan right] [Truck left] [Truck right] [Pedestal up] [Pedestal down]
    [Tilt up] [Tilt down] [Zoom in] [Zoom out] [Shake] [Tracking shot]
    [Static shot].
  - At most three simultaneous commands, written in one bracket:
    [Pan left,Pedestal up]. Sequential moves get their own brackets later in
    the prompt.
  - [Push in] and [Zoom in] are NOT the same move. Push in travels through
    space and changes parallax; zoom only changes focal length. Pick one.
  - Do not mix pan with truck, or tilt with pedestal, in one shot.
  - One dominant move per clip. Stacking moves is the most common failure.
  - There is no negative_prompt on H3. Write exclusions as plain sentences.
  - Named camera terms land; adjectives like "cinematic", "epic", "dynamic" do
    not. Say what the camera does instead.
