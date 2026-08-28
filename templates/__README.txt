Editable text that shapes every prompt. No code involved - change these files
and re-run `mvkit build <song>`.

  cameras.txt     the three camera setups (v1 wide / v2 angle / v3 detail)
  sections.txt    H3's six prompt sections and what belongs in each
  drafting.txt    the brief handed to Claude or the local LLM when it writes
                  content.json - the single place to tune how shots are worded
  styles/         look blocks. Copy one to <song>/_source/style.txt and edit.
  bible/          cast and world blocks
  tail/           the closing block appended to every scene (sound, negatives)

A song may override any of cameras.txt / sections.txt / drafting.txt by putting
its own copy in <song>/_source/. Lines starting with # are comments and are
stripped before the text reaches the model.
